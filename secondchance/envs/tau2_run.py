"""Run one continuation from a tau2-bench checkpoint (telecom, banking, retail, airline), as the evaluation did.

The checkpoint is restored and verified (tau2_env.restore); its history becomes the task's starting message history; tau2-bench's own
orchestrator then runs the agent (tau2's llm_agent, any LiteLLM model string, e.g. "openai/<served name>" with api_base for an
OpenAI-compatible endpoint) against tau2's user simulator. The assistance text of the condition (N, L, PA; none for U) is appended to
the agent's system prompt; the user simulator never sees it. The step limit is tau2's own episode limit (200 orchestrator steps) counted
from the start of the episode, so a continuation gets 200 minus the steps already in its history. The record is written in the layout the
scorer reads (secondchance.scoring.score.score_tau2)."""
from __future__ import annotations

import json
import time
from pathlib import Path

from secondchance.envs import tau2_env

EPISODE_STEPS = 200


def steps(history):
    """tau2 orchestrator steps of a message list: one per agent or user message, plus one environment step per tool-calling message"""
    return sum(1 for m in history if m["role"] in ("assistant", "user")) + sum(1 for m in history if m["role"] in ("assistant", "user") and m.get("tool_calls"))


def message_dict(m):
    d = {"role": getattr(m, "role", None), "content": getattr(m, "content", None),
         "tool_calls": [{"id": t.id, "name": t.name, "arguments": t.arguments, "requestor": getattr(t, "requestor", None)} for t in (getattr(m, "tool_calls", None) or [])]}
    for k in ("id", "requestor", "error", "usage"):
        if hasattr(m, k):
            v = getattr(m, k)
            d[k] = v.model_dump() if hasattr(v, "model_dump") else v
    return d


def run(ck, condition, agent_model, agent_args=None, user_model="gpt-4.1-2025-04-14", user_args=None, seed=0, completion=None):
    """Returns the continuation record. completion: an optional stand-in for litellm.completion (tests replay recorded turns with it)."""
    import tau2.utils.llm_utils as LU
    from tau2.agent.llm_agent import LLMAgent
    from tau2.data_model.message import AssistantMessage, UserMessage
    from tau2.data_model.simulation import TextRunConfig
    from tau2.data_model.tasks import InitialState
    from tau2.registry import registry
    from tau2.runner.batch import run_single_task

    from secondchance.scoring import tau2_reference as REF

    env, task_orig, hist, report = tau2_env.restore(ck)
    if not report["ok"]:
        raise RuntimeError(f"{ck.id}: restoration does not reproduce the recorded state: {report}")
    domain = ck.restore["domain"]
    task = task_orig.model_copy(deep=True)
    if task.initial_state is None:
        task.initial_state = InitialState(initialization_data=None, initialization_actions=None, message_history=hist)
    else:
        task.initial_state.message_history = hist
    ck_db = json.loads(env.tools.db.model_dump_json())
    text = ck.assistance(condition)
    orig_prompt = LLMAgent.system_prompt
    orig_completion = LU.completion
    shown = {}

    def system_prompt(self):  # the agent's prompt plus the condition's text; recorded, since the semantic review gives it to the judge as the policy
        shown["prompt"] = orig_prompt.fget(self) + ("\n\n" + text if text else "")
        return shown["prompt"]
    LLMAgent.system_prompt = property(system_prompt)
    if completion is not None:
        LU.completion = completion
    from tau2.orchestrator.orchestrator import Orchestrator
    seen = {"trajectory": []}
    orig_step = Orchestrator.step

    def step(self):  # keep every message produced so far: a run that stops on the context window is scored on what it did
        try:
            orig_step(self)
        finally:
            seen["trajectory"] = list(self.trajectory)
    Orchestrator.step = step
    budget = EPISODE_STEPS - steps(ck.history)
    cfg = TextRunConfig(domain=domain, agent="llm_agent", llm_agent=agent_model, llm_args_agent={"temperature": 0.0, "seed": seed, **(agent_args or {})},
                        user="user_simulator", llm_user=user_model, llm_args_user={"temperature": 0.0, **(user_args or {})},
                        **({"retrieval_config": "bm25_grep"} if domain == "banking_knowledge" else {}), max_steps=budget, max_errors=10, seed=seed)
    t0 = time.time()
    try:
        try:
            sim = run_single_task(cfg, task, seed=seed)
        except Exception as e:  # noqa: BLE001  (a context-window stop ends the run; anything else is an infrastructure failure)
            msg = f"{type(e).__name__}: {e}"
            kind = "CONTEXT_STOP" if "ContextWindowExceeded" in msg or "maximum context length" in msg else "INFRASTRUCTURE_FAILURE"
            part = seen["trajectory"][len(hist):]
            return {"setting": f"tau2_{domain}", "task": ck.restore["task"], "checkpoint_id": ck.id, "cond": condition, "seed": seed, "status": kind,
                    "error": msg[:4000], "termination": {"reason": kind}, "history": ck.history, "continuation": [message_dict(m) for m in part],
                    "restore": report, "checkpoint_db": ck_db, "agent_model": agent_model, "user_model": user_model,
                    "assistance": {"condition": condition, "text": text, "placement": "agent system prompt (appended)" if text else "none"},
                    "agent_system_prompt": shown.get("prompt")}
    finally:
        LLMAgent.system_prompt = orig_prompt
        LU.completion = orig_completion
        Orchestrator.step = orig_step
    msgs = sim.messages
    n = len(hist)
    prefix_ok = len(msgs) >= n and all(a.content == b.content for a, b in zip(msgs[:n], hist))
    cont = msgs[n:] if prefix_ok else msgs
    probe = registry.get_env_constructor(domain)()
    new_calls = [tc for m in cont if isinstance(m, (AssistantMessage, UserMessage)) and m.is_tool_call() for tc in m.tool_calls]
    mutating = [tc for tc in new_calls if probe._has_tool(tc.name) and probe._is_mutating_tool(tc.name)]
    end_env = REF._env(domain, task_orig)
    for m in msgs:
        if isinstance(m, (AssistantMessage, UserMessage)) and m.is_tool_call():
            for tc in m.tool_calls:
                end_env.get_response(tc)
    term = str(sim.termination_reason).lower()
    status = "BUDGET_STOP" if "max_steps" in term else "TOOL_ERROR_STOP" if "too_many_errors" in term else "ERROR_TERMINATION" if "error" in term else "COMPLETED"
    ri = sim.reward_info
    return {"setting": f"tau2_{domain}", "task": ck.restore["task"], "checkpoint_id": ck.id, "cond": condition, "seed": seed, "status": status,
            "budget_steps": budget, "agent_model": agent_model, "user_model": user_model, "restore": report, "history_prefix_preserved": prefix_ok,
            "assistance": {"condition": condition, "text": text, "placement": "agent system prompt (appended)" if text else "none"},
            "termination": {"reason": str(sim.termination_reason), "continuation_messages": len(cont), "wall_seconds": round(time.time() - t0, 1)},
            "reward_info": json.loads(ri.model_dump_json()) if ri is not None else None,
            "n_new_tool_calls": len(new_calls), "new_mutating_calls": [[tc.name, tc.arguments] for tc in mutating],
            "checkpoint_db": ck_db, "end_db": json.loads(end_env.tools.db.model_dump_json()),
            "user_turns": sum(1 for m in cont if m.role == "user" and (m.content or "").strip()),
            "history": [message_dict(m) for m in hist], "continuation": [message_dict(m) for m in cont], "agent_system_prompt": shown.get("prompt")}


def replay_completion(record, agent_model, user_model):
    """A stand-in for litellm.completion that returns a recorded run's agent and user turns in order (tests; no model is called)."""
    from litellm.types.utils import ChatCompletionMessageToolCall, Choices, Function, Message, ModelResponse, Usage
    turns = {"agent": [m for m in record["continuation"] if m["role"] == "assistant"], "user": [m for m in record["continuation"] if m["role"] == "user"]}
    pos = {"agent": 0, "user": 0}

    def fake(model=None, messages=None, tools=None, tool_choice=None, **kw):
        who = "agent" if model == agent_model else "user"
        m = turns[who][pos[who]]
        pos[who] += 1
        calls = [ChatCompletionMessageToolCall(id=t["id"], type="function", function=Function(name=t["name"], arguments=json.dumps(t["arguments"])))
                 for t in m.get("tool_calls") or []] or None
        msg = Message(role="assistant", content=m.get("content"), tool_calls=calls)
        return ModelResponse(choices=[Choices(index=0, message=msg, finish_reason="tool_calls" if calls else "stop")],
                             usage=Usage(prompt_tokens=0, completion_tokens=0, total_tokens=0), model=model)
    return fake
