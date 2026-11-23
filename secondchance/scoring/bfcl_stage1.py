"""Stage 1 for BFCL with the correction target of the checkpoint (an unwanted change: every protected attribute at its initial value)."""
from __future__ import annotations

import copy, functools, json, re, sys  # noqa: F401,E401
from pathlib import Path  # noqa: F401
from secondchance.scoring import bfcl_stage1_base as A1  # noqa: E402
from secondchance.scoring import bfcl_state as BW  # noqa: E402
from secondchance.scoring import bfcl_backends as IC  # noqa: E402
from secondchance.scoring import bfcl_reference as W  # noqa: E402
from secondchance.envs import bfcl_env as BM  # noqa: E402
from secondchance.scoring import milestones as M  # noqa: E402


BW, IC, W, BM, M = A1.BW, A1.IC, A1.W, A1.BM, A1.M


VERSION = "secondchance 1.0"


def _get(st, k):
    return st.get(f"{k[0]}.{k[1]}", st.get(k))


def targets(e, div, restated_attrs=()):
    init = BW.vals(IC.fresh(e))
    rb = IC.fresh(e)
    for turn in W.gt_calls(e):
        for n, a in turn:
            rb.call(n, BM._bind_positional(rb, n, copy.deepcopy(a)))
    ref_end = BW.vals(rb)
    keys = [k for k in init if f"{k[0]}.{k[1]}" in set(div["attributes"]) | set(restated_attrs)]
    tgt = {k: ref_end.get(k, "<absent>") for k in keys}
    if div["type"] == "P":
        traj = [W.flat(IC.fresh(e).state())] + [W.flat(s) for s in BM.reference_states(e)]
        tgt = {k: init[k] for k in init if all(_get(st, k) == _get(traj[0], k) for st in traj)}
        tgt.update({k: init[k] for k in keys})
    return tgt, init, ref_end


def _score_calls_v1_fixed(entry_id, calls, k0, div, turn_checks=None, cont_msgs=None, restated_attrs=()):
    orig = A1.targets
    A1.targets = targets
    try:
        return A1.score_calls(entry_id, calls, k0, div, turn_checks, cont_msgs, restated_attrs)
    finally:
        A1.targets = orig


def score_calls(entry_id, calls, k0, div, turn_checks=None, cont_msgs=None, restated_attrs=()):
    out = _score_calls_v1_fixed(entry_id, calls, k0, div, turn_checks, cont_msgs, restated_attrs)
    if restated_attrs:
        proxy = _score_calls_v1_fixed(entry_id, calls, k0, div, turn_checks, cont_msgs, ())
        out["bank_proxy_target"] = {"correction_first": proxy["milestones"]["correction_first"]["status"],
                                    "correction_final": proxy["milestones"]["correction_final"]["status"], "attributes": div["attributes"],
                                    "note": "audit only: the recorded proxy attribute; the outcome is the restated target in `milestones`"}
        out["correction_target"] = {"restated": list(restated_attrs), "recorded_proxy": div["attributes"]}
    out["adapter"] = VERSION
    return out
