"""Figure 2: observed recoverability with a plan on the 57 checkpoints with a demonstrated fix. One column per checkpoint, sorted within its
environment by the number of models that correct it (ties: more complete recoveries, then more unaided corrections, then checkpoint id);
one row per model in the order of Table 3. R complete recovery, C corrected but not complete, 0 not corrected, n not run.
  python scripts/figure2.py            prints the grid
  python scripts/figure2.py out.png    also renders it (needs matplotlib)"""
import sys

from common import MODELS, NAMES, checkpoints, load

PANEL = {"tau2": "tau2-bench ({n} checkpoints)", "bfcl": "BFCL ({n} checkpoints)", "appworld": "AppWorld ({n} checkpoints)"}


def grid():
    runs = {(r["checkpoint_id"], r["model"], r["condition"]): r for r in load("main_study")}
    cks = checkpoints()
    out = {}
    for env in ("tau2", "bfcl", "appworld"):
        ids = sorted(c for c, x in cks.items() if x["environment"] == env and x["split"] == "main" and x["fixability"] == "demonstrated")

        def code(ck, m, cond):
            r = runs.get((ck, m, cond))
            if r is None:
                return "n"
            if r["status"] == "protocol_excluded":
                return "x"
            return "R" if r["status"] == "scored" and r["complete_recovery"] else ("C" if r["status"] == "scored" and r["corrected_end"] else "0")

        def ease(ck):
            return (-sum(code(ck, m, "PA") in "RC" for m in MODELS), -sum(code(ck, m, "PA") == "R" for m in MODELS),
                    -sum(code(ck, m, "U") in "RC" for m in MODELS), ck)
        ids.sort(key=ease)
        out[PANEL[env].format(n=len(ids))] = [[NAMES[m], "".join(code(c, m, "PA") for c in ids)] for m in MODELS]
    return out


def render(path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    g = grid()
    colour = {"R": "#2F6DB5", "C": "#B5CCE8", "0": "white", "n": "#DBDBDB", "x": "#DBDBDB"}
    fig, ax = plt.subplots(figsize=(13, 3.6))
    x0 = 0
    for title, rows in g.items():
        ax.text(x0, 0.3, title.replace("tau2-bench", "τ²-bench"), fontsize=9, weight="bold")
        for j, (_, s) in enumerate(rows):
            for i, ch in enumerate(s):
                ax.add_patch(Rectangle((x0 + i, -j - 1), 0.85, 0.85, facecolor=colour[ch], edgecolor="#BFBFBF", linewidth=0.3))
        x0 += len(rows[0][1]) + 2
    for j, m in enumerate(MODELS):
        ax.text(-0.5, -j - 0.55, NAMES[m], fontsize=8, ha="right", va="center")
    ax.set_xlim(-9, x0); ax.set_ylim(-len(MODELS) - 1.5, 1); ax.axis("off")
    for k, (lab, ch) in enumerate((("complete recovery", "R"), ("corrected, not complete", "C"), ("not corrected", "0"), ("not run", "n"))):
        ax.add_patch(Rectangle((k * 14, -len(MODELS) - 1.4), 0.85, 0.6, facecolor=colour[ch], edgecolor="#BFBFBF", linewidth=0.3))
        ax.text(k * 14 + 1.2, -len(MODELS) - 1.1, lab, fontsize=8, va="center")
    fig.savefig(path, dpi=200, bbox_inches="tight")


if __name__ == "__main__":
    for title, rows in grid().items():
        print(title)
        for name, s in rows:
            print(f"  {name:18s} {s}")
    if len(sys.argv) > 1:
        render(sys.argv[1])
