"""Table 18 (Appendix E.4): correction durability. Plan-assisted runs ever corrected (at some observed state), runs that undid a correction
at least once, and runs corrected at termination; the last column counts runs with a regression in U, N and L together. A run can
regress and correct again. The corrected-state control (CS) starts corrected.
  python scripts/table18.py"""
from common import NAMES, counted, load, show


def line(name, runs):
    pa = [r for r in runs if r["condition"] == "PA"]
    np_ = [r for r in runs if r["condition"] != "PA"]
    t = lambda r, f: r.get(f) is True  # noqa: E731
    return [name, str(sum(t(r, "corrected_ever") for r in pa)), str(sum((r.get("n_regressions") or 0) > 0 for r in pa)),
            str(sum(t(r, "corrected_end") for r in pa)), str(sum((r.get("n_regressions") or 0) > 0 for r in np_))]


def rows():
    main = counted(load("main_study"))
    out = [["Main study"]]
    for env, lab in (("bfcl", "BFCL"), ("tau2", "tau2"), ("appworld", "AppWorld")):
        out.append(line(lab, [r for r in main if r["environment"] == env]))
    out.append(["Repeated and hosted study"])
    rep, hosted = load("repeated"), load("hosted_three_sample")
    for env, lab, n_open in (("bfcl", "BFCL", "ten"), ("tau2", "tau2", "five")):
        out.append(line(f"{lab}: {n_open} open models", [r for r in rep if r["environment"] == env]))
        for m in ("gpt-5.4-mini", "gpt-5.5", "gpt-6.1-sol"):
            out.append(line(f"{lab}: {NAMES[m]}", [r for r in hosted if r["environment"] == env and r["model"] == m]))
    cs = [r for r in load("competence_controls") if r["condition"] == "CS"]
    out.append(["Corrected-state control", str(len(cs)), str(sum(r["n_regressions"] > 0 for r in cs)), str(sum(r["corrected_end"] for r in cs)), "--"])
    return out


if __name__ == "__main__":
    show([["Population", "PA ever", "PA regr.", "PA end", "U, N, L regr."]] + rows())
