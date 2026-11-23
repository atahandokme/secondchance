"""Corrective writes: executed, error-free, state-changing calls after the checkpoint that move an erroneous field to its target, with who made them (the agent, or the user's own device actions)."""
from __future__ import annotations

import json, re  # noqa: F401,E401
from secondchance.scoring import tau2_stage1 as A  # noqa: E402


def corrective_writes(rec, cut_messages, effects):
    C, P, W = A.C, A.P, A.W
    d, task, msgs = C.domain_of(rec), C.task_of(rec), C.messages(rec)
    snaps, rows = W.trace(d, task, msgs)
    k0 = sum(1 for r in rows if r["msg"] < cut_messages)
    out = []
    for i in range(k0, len(rows)):
        r = rows[i]
        if not r.get("mutating") or r.get("error"):
            continue
        before, after = C.state_fields(snaps[i]), C.state_fields(snaps[i + 1])
        moved = [e["field"] for e in effects if P.correction([e], before)["value"] is not True and P.correction([e], after)["value"] is True]
        if moved:
            out.append({"msg": r["msg"] - cut_messages, "call": r["name"], "arguments": r.get("arguments"), "requestor": r.get("requestor"), "fields": moved})
    return out


def summary(rec, cut_messages, effects):
    w = corrective_writes(rec, cut_messages, effects)
    ag = [x for x in w if x["requestor"] == "assistant"]
    us = [x for x in w if x["requestor"] != "assistant"]
    return {"status": "AGENT" if ag else ("USER_ONLY" if us else "NONE"), "agent": ag, "user": us}
