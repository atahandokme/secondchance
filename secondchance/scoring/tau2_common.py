"""tau2-bench helpers used by scoring: environment and task construction, record messages, tool calls in order, flattened agent and user database fields."""
from __future__ import annotations

import copy, functools, json, re, sys  # noqa: F401,E401
from pathlib import Path  # noqa: F401


H = Path(__file__).resolve().parents[2]


POOLS = {"tau2_telecom": {"split": None}, "tau2_banking_knowledge": {"split": None}}  # tau2 task sets, default split


_SETUP = False


def setup():
    global _SETUP
    if _SETUP:
        return
    import tau2.domains.banking_knowledge.environment as _BE, tau2.domains.banking_knowledge.retrieval as _BR
    _BE.DEFAULT_RETRIEVAL_VARIANT = _BR.DEFAULT_RETRIEVAL_VARIANT = "bm25_grep"
    import tau2.knowledge.embedders.openai_embedder as _OE, tau2.knowledge.embedders.openrouter_embedder as _ORE

    def _blocked(*a, **k):
        raise RuntimeError("hosted embedding call blocked (SecondChance scoring is offline)")
    for _m in (_OE, _ORE):
        for _n in dir(_m):
            if _n.endswith("Embedder") and isinstance(getattr(_m, _n), type):
                getattr(_m, _n).__init__ = _blocked
    try:
        from loguru import logger
        logger.remove()
    except Exception:  # noqa: BLE001
        pass
    _SETUP = True


def domain_of(rec):
    return "telecom" if "telecom" in rec["setting"] else "banking_knowledge"


@functools.lru_cache(maxsize=None)
def _task(d, tid):
    setup()
    from tau2.run import get_tasks
    return get_tasks(d, task_split_name=POOLS[f"tau2_{d}"]["split"], task_ids=[tid])[0]


def task_of(rec):
    return _task(domain_of(rec), rec["task"])


def load(f):
    return json.loads(Path(f).read_text())


def messages(rec):
    """Full message list of a record: history + continuation (natives: history empty, cut 0)."""
    return (rec.get("history") or []) + (rec.get("continuation") or [])


def tool_calls(msgs):
    from tau2.data_model.message import ToolCall
    out = []
    for i, m in enumerate(msgs):
        if m["role"] in ("assistant", "user") and m.get("tool_calls"):
            for tc in m["tool_calls"]:
                out.append((i, ToolCall(id=tc.get("id") or "x", name=tc["name"], arguments=tc.get("arguments") or {},
                                        requestor=tc.get("requestor") or ("user" if m["role"] == "user" else "assistant"))))
    return out


def fresh(d, task):
    setup()
    from secondchance.scoring.tau2_reference import _env
    return _env(d, task)


def dbs(env):
    a = json.loads(env.tools.db.model_dump_json()) if env.tools is not None and env.tools.db is not None else None
    u = json.loads(env.user_tools.db.model_dump_json()) if getattr(env, "user_tools", None) is not None and env.user_tools.db is not None else None
    return a, u


def hashes(env):
    return {"agent_db_hash": env.get_db_hash(), "user_db_hash": env.get_user_db_hash()}


def _key(x):
    for k in x:
        if k.endswith("_id") and isinstance(x[k], (str, int)):
            return f"{k}={x[k]}"
    return None


def flat(v, p=""):
    """Leaf-level flattening; lists of dicts carrying an *_id key are keyed by that id (stable under insertion), other lists by index."""
    if isinstance(v, dict):
        out = {}
        for k, x in v.items():
            out.update(flat(x, f"{p}.{k}" if p else str(k)))
        return out or {p: "{}"}
    if isinstance(v, list):
        out = {}
        for j, x in enumerate(v):
            kk = _key(x) if isinstance(x, dict) else None
            out.update(flat(x, f"{p}[{kk or j}]"))
        return out or {p: "[]"}
    return {p: json.dumps(_canon(v), sort_keys=True)}


_INTF = __import__("re").compile(r"(?<![\d.])(\d+)\.0(?![\d.])")


def _canon(v):
    """Field comparison only; restoration hashes are never normalized."""
    if isinstance(v, float) and v.is_integer():
        return int(v)
    if isinstance(v, str):
        return _INTF.sub(r"\1", v)
    return v


def user_db_shared(env):
    return getattr(env, "user_tools", None) is not None and env.tools is not None and env.user_tools.db is env.tools.db


def state_fields(env):
    """agent DB fields ("a:") + user DB fields ("u:"); banking's user toolkit shares the agent DB object, so it is not counted twice."""
    a, u = dbs(env)
    out = {f"a:{k}": v for k, v in flat(a or {}).items()}
    if not user_db_shared(env):
        out.update({f"u:{k}": v for k, v in flat(u or {}).items()})
    return out


def entity_of(path):
    """'a:lines[line_id=L1002].roaming_enabled' -> 'a:lines[line_id=L1002]'; user device fields -> 'u:device'."""
    head = path.split(".")[0] if "." in path else path
    return head


def gold_actions(task):
    return task.evaluation_criteria.actions or []


def gold_env(d, task, skip=frozenset()):
    from secondchance.scoring.tau2_reference import _apply_gold
    g = fresh(d, task)
    errs = _apply_gold(g, task, skip)
    return g, errs
