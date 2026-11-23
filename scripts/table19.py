"""Table 19 (Appendix F.1): BFCL competence controls, counts out of 180 cells (18 checkpoints x ten open-weight models) per condition,
correction at termination. U and PA are the main-study runs of the same cells; PO adds the exact corrective calls to the plan; CS starts
from the corrected state and history; the clean start is the source episode of the same model and task (no error to correct).
  python scripts/table19.py"""
from common import checkpoints, load, show, yes


def rows():
    cks = {c for c, x in checkpoints().items() if x["competence_control"]}
    main = [r for r in load("main_study") if r["checkpoint_id"] in cks and r["model"] not in ("gpt-6.1-sol", "gpt-5.4-mini")]
    ctrl = load("competence_controls")
    # clean start: the source episode of the same model and task, run from the task's initial state
    ep = {(e["task_id"], e["source_model"]): e for e in load("source_episodes")}
    cells = {(r["checkpoint_id"], r["task_id"], r["model"]) for r in ctrl}  # two control checkpoints share a task: one episode, two cells
    assert len(cells) == 180
    out = [["Clean start", "--", str(sum(ep[(t, m)]["task_success"] for _, t, m in cells)), "--"]]
    for name, x in (("U", [r for r in main if r["condition"] == "U"]), ("PA", [r for r in main if r["condition"] == "PA"]),
                    ("PO: exact calls", [r for r in ctrl if r["condition"] == "PO"]), ("CS: corrected", [r for r in ctrl if r["condition"] == "CS"])):
        assert len(x) == 180, name
        out.append([name] + [str(sum(yes(r, f) for r in x)) for f in ("corrected_end", "task_success", "complete_recovery")])
    return out


if __name__ == "__main__":
    show([["Condition", "Corrected", "Task success", "Complete"]] + rows())
