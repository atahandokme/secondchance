"""Table 5 (Appendix A): kinds of error of the 129 checkpoints and the fixability established for each before evaluation.
  python scripts/table5.py"""
from collections import Counter

from common import checkpoints, show

ORDER = {"tau2": ("wrong value", "wrong entity", "unrequested change", "policy-forbidden action"),
         "bfcl": ("unwanted change elsewhere", "wrong entity", "wrong value", "wrong value and unwanted change"),
         "appworld": ("several effects", "unwanted record in a task table", "record removed", "unwanted record elsewhere", "wrong value on a task record",
                      "unrelated record modified")}
TITLE = {"tau2": "tau2-bench ({n})", "bfcl": "BFCL ({n})", "appworld": "AppWorld ({n})"}
FIX = ("demonstrated", "proven_impossible", "unknown")


def rows():
    cks = [c for c in checkpoints().values() if c["split"] == "main"]
    out = []
    for env, kinds in ORDER.items():
        mine = [c for c in cks if c["environment"] == env]
        assert {c["error_kind"] for c in mine} == set(kinds), env
        out.append([TITLE[env].format(n=len(mine))])
        for k in kinds:
            n = Counter(c["fixability"] for c in mine if c["error_kind"] == k)
            out.append([k] + [str(n[f]) if n[f] else "--" for f in FIX])
    tot = Counter(c["fixability"] for c in cks)
    out.append(["Total"] + [str(tot[f]) for f in FIX])
    return out


if __name__ == "__main__":
    show([["Kind of error", "Fix demonstrated", "Proven impossible", "Unknown"]] + rows())
