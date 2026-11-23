"""Stage 1 for BFCL: correction at every executed call, protection and the per-turn goal at termination."""
from __future__ import annotations

import copy, functools, json, re, sys  # noqa: F401,E401
from pathlib import Path  # noqa: F401
from secondchance.scoring import bfcl_state as BW  # noqa: E402
from secondchance.scoring import milestones as M  # noqa: E402
from secondchance.scoring import bfcl_backends as IC  # noqa: E402
from secondchance.scoring import bfcl_reference as W  # noqa: E402
from secondchance.envs import bfcl_env as BM  # noqa: E402


IC, W, BM = BW.IC, BW.W, BW.BM


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
        tgt = {k: init[k] for k in init if all(st.get(f"{k[0]}.{k[1]}") == traj[0].get(f"{k[0]}.{k[1]}") for st in traj)}
        tgt.update({k: init[k] for k in keys})
    return tgt, init, ref_end


def score_calls(entry_id, calls, k0, div, turn_checks=None, cont_msgs=None, restated_attrs=()):
    """calls: every executed call of the episode in order (prefix + continuation); k0 = number of prefix calls (the checkpoint)."""
    e = W.ENT[entry_id]
    tgt, init, _ = targets(e, div, restated_attrs)
    b = IC.fresh(e)
    for c in calls[:k0]:
        b.call(c["name"], copy.deepcopy(c["arguments"]))
    obs = [{"msg": 0, "call": "checkpoint", "correction": BW.meets(b, tgt) if tgt else None}]
    for c in calls[k0:]:
        b.call(c["name"], copy.deepcopy(c["arguments"]))
        obs.append({"msg": c.get("message_index"), "call": c["name"], "correction": BW.meets(b, tgt) if tgt else None})
    rb = IC.fresh(e); traj = [W.flat(rb.state())] + [W.flat(s) for s in BM.reference_states(e)]
    init_flat = traj[0]
    prot = {k: v for k, v in init.items() if all(st.get(f"{k[0]}.{k[1]}", st.get(k)) == init_flat.get(f"{k[0]}.{k[1]}", init_flat.get(k)) for st in traj)}
    obs[-1]["protection"] = BW.meets(b, {k: init[k] for k in prot}) if prot else None
    obs[-1]["goal"] = (all(t["state_matches_reference"] for t in turn_checks) if turn_checks else None)
    msgs = cont_msgs or []
    final = next((m.get("content") for m in reversed(msgs) if m.get("role") == "assistant" and (m.get("content") or "").strip()), None)
    rep = {"status": "ABSENT", "why": "no assistant text"} if not final else {"status": "UNKNOWN", "why": "truth needs the frozen judge", "final_text": final[:300]}
    return M.score(obs, msgs, "per_executed_call", consent_rows=[], report=rep, extra={"consent_applicability": "NOT_APPLICABLE (scripted user)",
                                                                                  "target_attributes": [f"{k[0]}.{k[1]}" for k in tgt]})
