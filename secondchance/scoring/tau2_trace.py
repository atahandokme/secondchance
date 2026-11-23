"""Replay of a tau2-bench conversation in a fresh environment, one snapshot after every executed tool call."""
from __future__ import annotations

import copy, functools, json, re, sys  # noqa: F401,E401
from pathlib import Path  # noqa: F401
from secondchance.scoring import tau2_common as C  # noqa: E402
from secondchance.scoring import tau2_predicates as P  # noqa: E402


def trace(d, task, msgs):
    env = C.fresh(d, task)
    tm = {m.get("id"): i for i, m in enumerate(msgs) if m["role"] == "tool"}
    snaps, rows = [copy.deepcopy(env)], []
    for k, (i, tc) in enumerate(C.tool_calls(msgs)):
        pre_db = C.dbs(env)[0]; pre = C.state_fields(env)
        r = env.get_response(tc)
        post = C.state_fields(env)
        rows.append({"k": k, "msg": i, "tool_msg": tm.get(tc.id), "name": tc.name, "requestor": tc.requestor, "arguments": tc.arguments,
                     "error": bool(r.error), "mutating": bool(env._has_tool(tc.name) and env._is_mutating_tool(tc.name)), "pre_db": pre_db,
                     "pre": pre, "post": post})
        snaps.append(copy.deepcopy(env))
    return snaps, rows
