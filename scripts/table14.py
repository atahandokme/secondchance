"""Table 14 (Appendix D): paired differences against U in percentage points, with 95% source-task bootstrap intervals.
A cell is (checkpoint, model) in the main study and (checkpoint, model, repetition) in the three-sample study; only cells in which all four
conditions have a model outcome are paired. Each interval uses 2,000 resamples of source tasks with random.Random(0): the main-study and
retail/airline rows draw a fresh generator for every comparison; the three-sample rows share one generator per environment and measure
across the comparisons N-U, L-U, PA-U and PA-L, in that order (PA-L is not printed), as in the paper.
  python scripts/table14.py"""
import random
from collections import defaultdict

from common import CONDS, fmt_pp, load, paired_pp, show, task_cluster

FIELDS = (("corrected_end", "c"), ("complete_recovery", "r"))
COMPARE = (("N", "U"), ("L", "U"), ("PA", "U"))


def cells(runs, key):
    by = defaultdict(dict)
    for r in runs:
        by[key(r)][r["condition"]] = r
    out = {}
    for k, v in by.items():
        if len(v) == 4 and all(v[c]["status"] == "scored" for c in CONDS):
            out[k] = {c: {f: int(v[c][f] is True) for f, _ in FIELDS} for c in CONDS}
    return out


def fresh_rows(label, runs, key):
    cl = cells(runs, key)
    row = [label, str(len(cl))]
    for f, _ in FIELDS:
        for a, b in COMPARE:
            est, lo, hi, _ = paired_pp(cl, a, b, f, random.Random(0))
            row.append(fmt_pp(est, lo, hi))
    return row


def shared_rows(label, runs, key):
    cl = cells(runs, key)
    row = [label, str(len(cl))]
    for f, _ in FIELDS:
        rng = random.Random(0)
        res = {}
        for a, b in COMPARE + (("PA", "L"),):
            res[(a, b)] = paired_pp(cl, a, b, f, rng)
        row += [fmt_pp(*res[(a, b)][:3]) for a, b in COMPARE]
    return row


def rows():
    main = [r for r in load("main_study") if r["status"] != "protocol_excluded"]
    mk = lambda r: (task_cluster(r), r["checkpoint_id"], r["model"])  # noqa: E731
    out = [["Main study, all checkpoints"]]
    for env, lab in (("tau2", "tau2"), ("bfcl", "BFCL"), ("appworld", "AppWorld")):
        out.append(fresh_rows(lab, [r for r in main if r["environment"] == env], mk))
    out.append(["Main study, checkpoints with a demonstrated fix"])
    for env, lab in (("tau2", "tau2"), ("bfcl", "BFCL"), ("appworld", "AppWorld")):
        out.append(fresh_rows(lab, [r for r in main if r["environment"] == env and r["fixability"] == "demonstrated"], mk))
    out.append(["Supporting studies"])
    ra = load("retail_airline")
    for env, lab in (("retail", "Retail"), ("airline", "Airline")):
        out.append(fresh_rows(lab, [r for r in ra if r["environment"] == env], mk))
    three = load("repeated") + load("hosted_three_sample")
    tk = lambda r: (task_cluster(r), r["checkpoint_id"], r["model"], r["repetition"])  # noqa: E731
    for env, lab in (("tau2", "tau2, three samples"), ("bfcl", "BFCL, three samples")):
        out.append(shared_rows(lab, [r for r in three if r["environment"] == env], tk))
    return out


if __name__ == "__main__":
    show(rows())
