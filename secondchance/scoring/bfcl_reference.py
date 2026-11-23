"""BFCL reference calls and state flattening."""
from __future__ import annotations

import copy, functools, json, re, sys  # noqa: F401,E401
from pathlib import Path  # noqa: F401
from secondchance.envs import bfcl_env as BM  # noqa: E402


ENT = {e["id"]: e for c in BM.CATEGORIES for e in BM.load_entries(c)}


def gt_calls(entry):
    return [[BM.parse_gt_call(c) for c in turn] for turn in entry["ground_truth"]]


def flat(state):
    return {(c, k): BM.canon(v) for c, attrs in state.items() for k, v in attrs.items()}


def executed_from_record(r):
    e = ENT[r["entry_id"]]
    if all(BM.restore(e, [c for c in r["executed_calls"] if c["turn"] <= t["turn"]])[0].state_hash() == t["state_hash"] for t in r["turn_checks"]):
        return r["executed_calls"], "executed_calls"
    msg = []
    for m in r["messages"]:
        if m["role"] == "assistant":
            for tc in m.get("tool_calls") or []:
                try:
                    a = json.loads(tc["arguments"] or "{}")
                except Exception:
                    a = None
                if isinstance(a, dict):
                    msg.append((tc["name"], a))
    ex = r["executed_calls"]
    if len(msg) == len(ex) and all(m[0] == c["name"] for m, c in zip(msg, ex)):
        return [{**c, "arguments": a} for (n, a), c in zip(msg, ex)], "message_argument_strings"
    return None, "UNRECONSTRUCTABLE"
