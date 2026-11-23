"""Run one continuation from a BFCL multi-turn checkpoint, as the evaluation did.

The checkpoint is restored and verified (bfcl_env.restore_checkpoint); the agent receives the harness's system prompt (plus the
condition's assistance text: N, L, PA; none for U) and the history, then the rest of the task: the remaining scripted user turns, with at
most 20 model steps per turn. Tool calls execute as method calls on the restored backends; after every turn the official per-turn state
check compares the backends with BFCL's reference. Task success requires every remaining turn to be present and matching. Messages are
sent in the OpenAI chat format through LiteLLM (model "openai/<served name>" with api_base for an OpenAI-compatible endpoint)."""
from __future__ import annotations

import json
import re
import time

from secondchance.envs import bfcl_env as B
from secondchance.scoring import bfcl_state  # noqa: F401  (every backend starts from pristine mutable defaults)

MAX_STEPS_PER_TURN = B.MAX_STEPS_PER_TURN


class ContextStop(Exception):
    pass


def call_model(comp, messages, tools, kw):
    """one call; if prompt + max_tokens exceeds the context, retry once with max_tokens = remaining context - 64 (at least 256)"""
    try:
        return comp(messages=messages, tools=tools, **kw)
    except Exception as e:  # noqa: BLE001
        t = str(e)
        if "maximum context length" not in t and "max_tokens must be at least 1" not in t:
            raise
        m = re.search(r"maximum context length is (\d+) tokens and your request has (\d+) input tokens", t)
        if "is too large" in t and m:
            room = int(m.group(1)) - int(m.group(2)) - 64
            if room >= 256:
                try:
                    return comp(messages=messages, tools=tools, **{**kw, "max_tokens": room})
                except Exception as e2:  # noqa: BLE001
                    if "maximum context length" in str(e2):
                        raise ContextStop(str(e2)[:300]) from e2
                    raise
        raise ContextStop(t[:300]) from e


def wire(messages, single_tool_call=False):
    """records keep tool calls as flat {id, name, arguments}; requests need {id, type, function}. single_tool_call: chat templates that
    accept one tool call per assistant message get N one-call messages, each followed by its result."""
    fmt = lambda tc: tc if "function" in tc else {"id": tc["id"], "type": "function", "function": {"name": tc["name"], "arguments": tc["arguments"]}}  # noqa: E731
    out, i = [], 0
    while i < len(messages):
        m = messages[i]
        if m.get("role") == "assistant" and "tool_calls" in m and not m["tool_calls"]:
            m = {k: v for k, v in m.items() if k != "tool_calls"}
        if m.get("role") == "assistant" and m.get("tool_calls"):
            tcs = [fmt(tc) for tc in m["tool_calls"]]
            if single_tool_call and len(tcs) > 1:
                j = i + 1
                results = {}
                while j < len(messages) and messages[j].get("role") == "tool":
                    results[messages[j].get("tool_call_id")] = messages[j]
                    j += 1
                for k, tc in enumerate(tcs):
                    out.append({**m, "content": m.get("content") if k == 0 else None, "tool_calls": [tc]})
                    if tc["id"] in results:
                        out.append(results.pop(tc["id"]))
                out += list(results.values())
                i = j
                continue
            m = {**m, "tool_calls": tcs}
        out.append(m)
        i += 1
    return out


def run(ck, condition, model, api_base=None, temperature=0.0, seed=0, max_tokens=4096, single_tool_call=False, completion=None, extra=None):
    """Returns the continuation record. completion: an optional stand-in for litellm.completion (tests replay recorded turns with it)."""
    backend, entry, report = B.restore_checkpoint(ck)
    if not report["ok"]:
        raise RuntimeError(f"{ck.id}: restoration does not reproduce the recorded state: {report}")
    if completion is None:
        import litellm
        completion = litellm.completion
    kw = {"model": model, "temperature": temperature, "seed": seed, "max_tokens": max_tokens, **({"api_base": api_base} if api_base else {}), **(extra or {})}
    text = ck.assistance(condition)
    messages = [{"role": "system", "content": B.SYSTEM + ("\n\n" + text if text else "")}] + json.loads(json.dumps(ck.history))
    rs = ck.restore["resume"]
    start_turn, mid_turn = rs["turn"], rs["mid_turn"]
    refs = B.reference_states(entry)
    turn_checks, executed, status, t0 = [], [], "COMPLETED", time.time()
    try:
        for t in range(start_turn, len(entry["question"])):
            if not (mid_turn and t == start_turn):  # resuming inside a turn: its user message is already in the history
                for um in entry["question"][t]:
                    messages.append({"role": "user", "content": um["content"]})
            tools = B.tools_for(entry, t)
            for _ in range(MAX_STEPS_PER_TURN):
                resp = call_model(completion, wire(messages, single_tool_call), tools, kw)
                msg = resp.choices[0].message
                tcs = msg.tool_calls or []
                messages.append({"role": "assistant", "content": msg.content, "tool_calls": [{"id": tc.id, "name": tc.function.name, "arguments": tc.function.arguments} for tc in tcs]})
                if not tcs:
                    break
                for tc in tcs:
                    try:
                        args = json.loads(tc.function.arguments or "{}")
                    except json.JSONDecodeError:
                        args = None
                    args_rec = json.loads(json.dumps(args)) if isinstance(args, dict) else args  # the backend may alias and later mutate arguments
                    out = backend.call(tc.function.name, args) if isinstance(args, dict) else "Error during execution: arguments are not valid JSON"
                    executed.append({"message_index": len(messages) - 1, "turn": t, "name": tc.function.name, "arguments": args_rec, "output": out})
                    messages.append({"role": "tool", "tool_call_id": tc.id, "content": out})
            else:
                status = "TURN_STEP_LIMIT"
            ok, diffs = B.turn_state_check(backend, refs[t])
            turn_checks.append({"turn": t, "state_matches_reference": ok, "differing": diffs, "state_hash": backend.state_hash()})
            if status == "TURN_STEP_LIMIT":
                break
    except ContextStop:
        status = "CONTEXT_STOP"
    return {"environment": "bfcl", "checkpoint_id": ck.id, "entry_id": entry["id"], "cond": condition, "model": model, "seed": seed, "temperature": temperature,
            "status": status, "wall_seconds": round(time.time() - t0, 1), "restore": {"state_hash": report["state_hash"], "replayed_calls": report["replayed_calls"],
                                                                                     "resume": rs},
            "messages": messages, "executed_calls": executed, "turn_checks": turn_checks,
            "official_style_success": bool(turn_checks) and all(c["state_matches_reference"] for c in turn_checks) and len(turn_checks) == len(entry["question"]) - start_turn,
            "assistance": {"condition": condition, "text": text, "placement": "system prompt (appended)" if text else "none"}}


def replay_completion(record, cut):
    """A stand-in for litellm.completion that returns a recorded run's assistant messages in order (tests; no model is called)."""
    from litellm.types.utils import ChatCompletionMessageToolCall, Choices, Function, Message, ModelResponse, Usage
    turns = [m for m in record["messages"][cut:] if m["role"] == "assistant"]
    pos = {"i": 0}

    def fake(messages=None, tools=None, **kw):
        m = turns[pos["i"]]
        pos["i"] += 1
        calls = [ChatCompletionMessageToolCall(id=t["id"], type="function", function=Function(name=t["name"], arguments=t["arguments"]))
                 for t in m.get("tool_calls") or []] or None
        return ModelResponse(choices=[Choices(index=0, message=Message(role="assistant", content=m.get("content"), tool_calls=calls),
                                              finish_reason="tool_calls" if calls else "stop")],
                             usage=Usage(prompt_tokens=0, completion_tokens=0, total_tokens=0), model=kw.get("model"))
    return fake
