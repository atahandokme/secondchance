"""Table 12 (Appendix D): the main study on all 129 checkpoints, per environment, model and condition: counts of runs with task success,
with the error corrected at the end, and with complete recovery. Runs per condition exclude protocol-excluded cells; a run without a
model outcome stays in the count.
  python scripts/table12.py"""
from common import CONDS, MODELS, NAMES, checkpoints, counted, load, show, yes

TITLE = {"tau2": "tau2-bench: {n} checkpoints", "bfcl": "BFCL: {n} checkpoints", "appworld": "AppWorld: {n} checkpoints, open-weight models"}


def rows():
    runs = counted(load("main_study"))
    cks = checkpoints()
    out = []
    for env in ("tau2", "bfcl", "appworld"):
        out.append([TITLE[env].format(n=sum(c["environment"] == env and c["split"] == "main" for c in cks.values()))])
        models = [m for m in MODELS if any(r["model"] == m and r["environment"] == env for r in runs)]
        for key, name in [(m, NAMES[m]) for m in models] + [(None, "All models")]:
            sel = [r for r in runs if r["environment"] == env and (key is None or r["model"] == key)]
            n = {c: sum(r["condition"] == c for r in sel) for c in CONDS}
            assert len(set(n.values())) == 1
            cells = []
            for c in CONDS:
                x = [r for r in sel if r["condition"] == c]
                cells.append("/".join(str(sum(yes(r, f) for r in x)) for f in ("task_success", "corrected_end", "complete_recovery")))
            out.append([name, str(n["U"])] + cells)
    return out


if __name__ == "__main__":
    show(rows())
