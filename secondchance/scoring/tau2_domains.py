"""Retail and airline in the tau2 helpers: the domain of a record and the task lookup (importing this module applies them)."""
from __future__ import annotations

import copy, functools, json, re, sys  # noqa: F401,E401
from pathlib import Path  # noqa: F401
from secondchance.scoring import tau2_common as C  # noqa: E402


RA = ("retail", "airline")


_orig_domain_of, _orig_task = C.domain_of, C._task


def domain_of(rec):
    s = rec["setting"]
    for d in RA:
        if s == f"tau2_{d}":
            return d
    return _orig_domain_of(rec)


@functools.lru_cache(maxsize=None)
def _task(d, tid):
    if d in RA:
        from tau2.run import get_tasks
        t = get_tasks(d, task_split_name=None, task_ids=[str(tid)])
        assert len(t) == 1 and t[0].id == str(tid), f"{d} task {tid} not found"
        return t[0]
    return _orig_task(d, tid)


C.domain_of, C._task = domain_of, _task
