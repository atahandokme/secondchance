"""BFCL backends built from pristine mutable defaults (BFCL's classes share mutable default lists and long-context globals)."""
from __future__ import annotations

import copy, functools, json, re, sys  # noqa: F401,E401
from pathlib import Path  # noqa: F401
from secondchance.envs import bfcl_env as BM  # noqa: E402
import inspect
import bfcl_eval.eval_checker.multi_turn_eval.func_source_code.long_context as _LC


_PRISTINE = {}


for _c, _m in BM.CLASS_FILE_PATH_MAPPING.items():
    if _c in BM.DOC_FILE:
        _C = getattr(__import__(_m, fromlist=[_c]), _c)
        for _n, _f in inspect.getmembers(_C, inspect.isfunction):
            if _f.__defaults__ and any(isinstance(d, (list, dict, set)) for d in _f.__defaults__):
                _PRISTINE[(_C, _n)] = copy.deepcopy(_f.__defaults__)


_LC_PRISTINE = {k: copy.deepcopy(v) for k, v in vars(_LC).items() if not k.startswith("_") and isinstance(v, (dict, list))}


def reset_defaults():
    dirty = []
    for k, v in _LC_PRISTINE.items():
        cur = getattr(_LC, k)
        if cur != v:
            dirty.append(f"long_context.{k}")
            if isinstance(cur, dict):
                cur.clear(); cur.update(copy.deepcopy(v))
            else:
                cur[:] = copy.deepcopy(v)
    for (C, n), d in _PRISTINE.items():
        if getattr(C, n).__defaults__ != d:
            dirty.append(f"{C.__name__}.{n}")
        getattr(C, n).__defaults__ = copy.deepcopy(d)
    return dirty


def fresh(entry):
    reset_defaults()
    return BM.Backend(entry)


def public(inst):
    return {k: v for k, v in vars(inst).items() if not k.startswith("_")}
