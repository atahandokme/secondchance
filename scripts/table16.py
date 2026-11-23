"""Table 16 (Appendix D.2): complete recoveries in the repeated and hosted tau2 study under complete recovery and the stricter consent-first
and strict readings. Rows with neither a complete recovery nor a held run are omitted.
  python scripts/table16.py"""
from common import CONDS, NAMES, load, show

OPEN = ("gemma-4-31b", "gpt-oss-120b", "llama-3.3-70b", "qwen3-235b", "qwen3-32b")
HOSTED = ("gpt-5.4-mini", "gpt-5.5", "gpt-6.1-sol")


def cells(x):
    n = lambda f, c: sum(r[f] == c for r in x)  # noqa: E731
    return [str(len(x)), str(n("recovery_class", "complete_recovery")), str(n("recovery_class", "held")), str(n("recovery_class_consent_first", "complete_recovery")),
            str(n("recovery_class_strict", "complete_recovery")), str(n("recovery_class_strict", "held"))]


def shown(c):
    return any(int(v) for v in c[1:])


def rows():
    runs = [r for r in load("repeated") + load("hosted_three_sample") if r["environment"] == "tau2"]
    out = []
    for cond in CONDS:
        c = cells([r for r in runs if r["model"] in OPEN and r["condition"] == cond])
        if shown(c):
            out.append(["Open models (five)", cond] + c)
            for m in OPEN:
                cm = cells([r for r in runs if r["model"] == m and r["condition"] == cond])
                if shown(cm):
                    out.append([NAMES[m], cond] + cm)
    for m in HOSTED:
        for cond in CONDS:
            c = cells([r for r in runs if r["model"] == m and r["condition"] == cond])
            if shown(c):
                out.append([NAMES[m], cond] + c)
    return out


if __name__ == "__main__":
    show([["Model", "Cond.", "Runs", "Compl.", "Held", "Consent-first compl.", "Strict compl.", "Strict held"]] + rows())
