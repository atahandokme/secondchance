"""Table 3: main evaluation on all 129 checkpoints, pooled over the environments each model was run in.
C = rate of runs that correct the error (at termination), R = rate of complete recoveries; n = runs per condition.
  python scripts/table3.py"""
from common import CONDS, MODELS, NAMES, counted, load, rate, show, yes


def rows():
    runs = counted(load("main_study"))
    out = []
    for key, name in [(m, NAMES[m]) for m in MODELS] + [(None, "All models")]:
        sel = [r for r in runs if key is None or r["model"] == key]
        n = {c: sum(r["condition"] == c for r in sel) for c in CONDS}
        assert len(set(n.values())) == 1
        cells = []
        for c in CONDS:
            x = [r for r in sel if r["condition"] == c]
            cells += [rate(sum(yes(r, "corrected_end") for r in x), n[c]), rate(sum(yes(r, "complete_recovery") for r in x), n[c])]
        out.append([name, f"{n['U']:,}"] + cells)
    return out


if __name__ == "__main__":
    show([["Model", "n", "U C", "U R", "N C", "N R", "L C", "L R", "PA C", "PA R"]] + rows())
