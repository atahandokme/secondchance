"""tau2-bench checkpoints (telecom, banking, and the retail and airline track): restore and replay verification.

A checkpoint is restored as in the frozen evaluation: a fresh tau2-bench environment for the task's initial state, then every tool call in
the visible history is replayed in order (agent calls and user-device calls). The restored agent and user databases must reproduce the
hashes recorded at evaluation time, and every replayed tool response must equal the recorded one (the wall-clock timing line of the
read-only banking KB_search output is the one declared normalization). Needs `pip install secondchance[tau2]` and the tau2-bench data
(TAU2_DATA_DIR pointing to the pinned commit's data/ folder)."""
import re

from secondchance.setup_env import data_dir

data_dir()  # tau2-bench reads TAU2_DATA_DIR when it is first imported
_TIMING = re.compile(r"\[Timing: retrieval=\d+ms, reranking=\d+ms, total=\d+ms\]")
_SETUP = set()


def setup(domain):
    """banking uses tau2's local bm25_grep retrieval (the default 'alltools' variant calls hosted embeddings), as in the evaluation"""
    if domain in _SETUP:
        return
    if domain == "banking_knowledge":
        import tau2.domains.banking_knowledge.environment as BE
        import tau2.domains.banking_knowledge.retrieval as BR
        BE.DEFAULT_RETRIEVAL_VARIANT = BR.DEFAULT_RETRIEVAL_VARIANT = "bm25_grep"
    _SETUP.add(domain)


def load_task(domain, task_id):
    from tau2.run import get_tasks
    for task_set in (domain, f"{domain}_full"):
        try:
            found = get_tasks(task_set, task_ids=[task_id])
        except Exception:  # noqa: BLE001  (task set or split absent in this tau2 version)
            continue
        if found:
            assert len(found) == 1 and found[0].id == task_id
            return found[0]
    raise KeyError(f"tau2 task {task_id!r} not found in domain {domain!r}")


def to_messages(history):
    from tau2.data_model.message import AssistantMessage, ToolCall, ToolMessage, UserMessage
    out = []
    for m in history:
        calls = [ToolCall(id=c["id"], name=c["name"], arguments=c["arguments"], requestor=c.get("requestor") or m["role"]) for c in m.get("tool_calls") or []] or None
        if m["role"] == "assistant":
            out.append(AssistantMessage(role="assistant", content=m.get("content"), tool_calls=calls))
        elif m["role"] == "user":
            out.append(UserMessage(role="user", content=m.get("content"), tool_calls=calls))
        elif m["role"] == "tool":
            out.append(ToolMessage(id=m["id"], role="tool", content=m.get("content"), requestor=m.get("requestor", "assistant"), error=m.get("error", False)))
        else:
            raise ValueError(m["role"])
    return out


def fresh_env(domain, task):
    from tau2.registry import registry
    env = registry.get_env_constructor(domain)()
    init = task.initial_state
    env.set_state(init.initialization_data if init else None, init.initialization_actions if init else None, [])
    return env


def restore(ck):
    """(environment at the checkpoint, task, history as tau2 messages, report). The report says whether the restoration reproduces the
    recorded hashes and tool responses; a continuation must not start unless report['ok']."""
    domain = ck.restore["domain"]
    setup(domain)
    task = load_task(domain, ck.restore["task"])
    msgs = to_messages(ck.history)
    calls = [tc for m in msgs if m.role in ("assistant", "user") and m.tool_calls for tc in m.tool_calls]
    tools = [m for m in msgs if m.role == "tool"]
    env = fresh_env(domain, task)
    mismatches = []
    for j, tc in enumerate(calls):
        got = str(env.get_response(tc).content)
        want = str(tools[j].content) if j < len(tools) else None
        if got != want and not (tc.name == "KB_search" and want is not None and _TIMING.sub("", got) == _TIMING.sub("", want)):
            mismatches.append(j)
    hashes = {"agent_db_hash": env.get_db_hash(), "user_db_hash": env.get_user_db_hash()}
    expected = ck.restore["expected_hashes"]
    match = {k: expected[k] == hashes[k] for k in expected if expected[k] is not None}
    report = {"checkpoint": ck.id, "replayed_calls": len(calls), "expected_replayed_calls": ck.restore["replayed_calls"], "mismatched_responses": mismatches,
              "hashes": hashes, "hashes_match": match}
    report["ok"] = not mismatches and all(match.values()) and len(calls) == ck.restore["replayed_calls"]
    return env, task, msgs, report
