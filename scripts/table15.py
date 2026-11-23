"""Table 15 (Appendix D.2): classes of the 279 runs sent to semantic review in the supporting studies (repeated and hosted tau2 runs,
the main-study tau2 runs of the five open-weight models of the repeated runs, and the retail and airline track), under complete recovery
and the stricter consent-first and strict readings. Only corrected runs that pass the mechanical checks reach review.
  python scripts/table15.py"""
from common import all_unique_runs, show

READ = (("Complete recovery", "recovery_class"), ("Consent-first", "recovery_class_consent_first"), ("Strict", "recovery_class_strict"))
CLASSES = ("complete_recovery", "correction_only", "held", "rejected")


def rows():
    rev = [r for r in all_unique_runs() if r.get("semantic_review") == "supporting"]
    assert len(rev) == 279
    out = []
    for name, f in READ:
        for i, (lab, sel) in enumerate((("U and PA", ("U", "PA")), ("N and L", ("N", "L")), ("All", ("U", "N", "L", "PA")))):
            x = [r for r in rev if r["condition"] in sel]
            out.append([name if i == 0 else "", lab, str(len(x))] + [str(sum(r[f] == c for r in x)) for c in CLASSES])
    return out


if __name__ == "__main__":
    show([["Reading", "Runs", "n", "Compl.", "Corr. only", "Held", "Rej."]] + rows())
