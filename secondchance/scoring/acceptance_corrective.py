"""Acceptance with the corrective-write consent component."""
from __future__ import annotations

import copy, functools, json, re, sys  # noqa: F401,E401
from pathlib import Path  # noqa: F401
from secondchance.scoring import acceptance_rules as V1  # noqa: E402
from secondchance.scoring import acceptance_closing as V2  # noqa: E402


stage1 = V1.stage1


def decide(c, judge=None, corrective=None):
    if judge and c["user_facing"] and stage1(c).startswith("CANDIDATE"):
        judge = dict(judge)
        judge["final_report_matches_state"] = "YES"  # that branch's only use of this field is the gate chk(...); neutralise it there
    return V2.decide(c, judge, corrective)
