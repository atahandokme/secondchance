"""Public BFCL backend attribute values and target checks."""
from __future__ import annotations

import copy, functools, json, re, sys  # noqa: F401,E401
from pathlib import Path  # noqa: F401
from secondchance.scoring import bfcl_reference as W  # noqa: E402
from secondchance.scoring import bfcl_backends as IC  # noqa: E402
from secondchance.envs import bfcl_env as BM  # noqa: E402
from collections import Counter


BM = W.BM


DIRTY = Counter()


_orig_init = BM.Backend.__init__


def _clean_init(self, entry):
    for d in IC.reset_defaults():
        DIRTY[d] += 1
    _orig_init(self, entry)


BM.Backend.__init__ = _clean_init


_orig_call = BM.Backend.call


def _runner_call(self, name, arguments):
    """Plain Backend.call (and so BM.restore) would execute it with no arguments."""
    if not isinstance(arguments, dict):
        out = "Error during execution: arguments are not valid JSON"
        self.executed.append({"name": name, "arguments": arguments, "output": out})
        return out
    return _orig_call(self, name, arguments)


BM.Backend.call = _runner_call


def vals(b):
    return {(c, a): v for c, inst in b.instances.items() for a, v in IC.public(inst).items()}


def meets(b, target):
    cur = vals(b)
    return all(cur.get(k, "<absent>") == v for k, v in target.items())


def executed_from_record(r):
    e = W.ENT[r["entry_id"]]
    ex = copy.deepcopy(r["executed_calls"])
    if all(BM.restore(e, copy.deepcopy([c for c in ex if c["turn"] <= t["turn"]]))[0].state_hash() == t["state_hash"] for t in r["turn_checks"]):
        return ex, "executed_calls"
    calls, src = W.executed_from_record(copy.deepcopy(r))
    return copy.deepcopy(calls), src
