"""Table 11 (Appendix D): diagnostic results on the 57 checkpoints with a demonstrated fix (main study, one run per cell).
No plan pools U, N and L. Ack.: the agent tells the user about the error (tau2 runs with a model outcome). C: corrected at termination.
Rep.: corrected with protected state intact. Task: task success. R: complete recovery. Kept: of the runs that ever corrected the error,
the share still corrected at termination. Chg.: share of tau2 runs that never correct the error and make another change to the affected
entity. Rates round exact halves up, as printed in the paper. Calls (plan-assisted runs): median per run rounded up to a whole call (Run), and total calls divided by complete recoveries (Rec.).
  python scripts/table11.py"""
import math

from common import MODELS, NAMES, counted, load, rate_half_up as rate, show, yes


def block(runs):
    G = runs
    n = len(G)
    cor = [r for r in G if yes(r, "corrected_end")]
    return {"n": n, "task": sum(yes(r, "task_success") for r in G), "corr": len(cor), "rep": sum(r["protected_state_intact"] is True for r in cor),
            "compl": sum(yes(r, "complete_recovery") for r in G), "ever": sum(yes(r, "corrected_ever") for r in G),
            "ack": [r.get("acknowledged") for r in G if r["environment"] == "tau2" and r["status"] == "scored"]}


def ackrate(b):
    # UNKNOWN: the judge's quote was not found in the record; it counts as not acknowledged (32 of the 1,795 tau2 judgments)
    assert all(a in ("YES", "NO", "UNKNOWN") for a in b["ack"])
    return rate(sum(a == "YES" for a in b["ack"]), len(b["ack"]))


def calls(pa):
    # AppWorld runs extended to the source episode's block limit: the paper's Table 11 counts the calls before the extension
    # (docs/reproduction_notes.md); Table 17 and the shipped agent_calls include the extension.
    c = [r["agent_calls_before_extension"] if r["agent_calls_before_extension"] is not None else r["agent_calls"] for r in pa if r["agent_calls"] is not None]
    compl = sum(yes(r, "complete_recovery") for r in pa)
    med = str(math.ceil(sorted(c)[len(c) // 2] if len(c) % 2 else (sorted(c)[len(c) // 2 - 1] + sorted(c)[len(c) // 2]) / 2)) if c else "--"
    rec = f"{sum(c) / compl:.0f}" if compl and len(c) == len(pa) else "--"
    return med, rec


def rows():
    runs = [r for r in counted(load("main_study")) if r["fixability"] == "demonstrated"]
    out = []
    for m in MODELS:
        row = [NAMES[m]]
        tb = [r for r in runs if r["model"] == m and r["environment"] in ("tau2", "bfcl")]
        np_, pa = block([r for r in tb if r["condition"] != "PA"]), block([r for r in tb if r["condition"] == "PA"])
        fc = [r["further_changes"] for r in tb if r["environment"] == "tau2" and r.get("further_changes") is not None]
        row += [ackrate(np_), rate(np_["corr"], np_["n"]), rate(np_["compl"], np_["n"]), ackrate(pa), rate(pa["task"], pa["n"]), rate(pa["corr"], pa["n"]),
                rate(pa["rep"], pa["n"]), rate(pa["compl"], pa["n"]), rate(pa["corr"], pa["ever"]), rate(sum(fc), len(fc))]
        row += list(calls([r for r in tb if r["condition"] == "PA"]))
        aw = [r for r in runs if r["model"] == m and r["environment"] == "appworld"]
        if not aw:
            row.append("-")  # hosted models were not run on AppWorld
        else:
            np_, pa = block([r for r in aw if r["condition"] != "PA"]), block([r for r in aw if r["condition"] == "PA"])
            row += [rate(np_["corr"], np_["n"]), rate(np_["compl"], np_["n"]), rate(pa["task"], pa["n"]), rate(pa["corr"], pa["n"]), rate(pa["rep"], pa["n"]),
                    rate(pa["compl"], pa["n"]), rate(pa["corr"], pa["ever"])]
            row += list(calls([r for r in aw if r["condition"] == "PA"]))
        out.append(row)
    return out


if __name__ == "__main__":
    show([["Model", "Ack", "C", "R", "Ack", "Task", "C", "Rep", "R", "Kept", "Chg", "Run", "Rec", "| AW C", "R", "Task", "C", "Rep", "R", "Kept", "Run", "Rec"]] + rows())
