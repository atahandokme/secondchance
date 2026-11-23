"""Table 10 (Appendix C.3): continuation jobs per study, counted from the shipped run files. Three-sample hosted runs that are also the
main-study run of their cell are counted once in the total.
  python scripts/table10.py"""
from common import load, show


def rows():
    main, ra, rep, hosted, ctrl = (load(s) for s in ("main_study", "retail_airline", "repeated", "hosted_three_sample", "competence_controls"))
    shared = sum(1 for r in hosted if r.get("also_main_study_run"))
    total = len({r["run_id"] for r in main + ra + rep + ctrl}) + len(hosted) - shared
    n_main_ck = len({r["checkpoint_id"] for r in main})
    tb = len({r["checkpoint_id"] for r in main if r["environment"] in ("tau2", "bfcl")})
    aw = len({r["checkpoint_id"] for r in main if r["environment"] == "appworld"})
    assert n_main_ck == tb + aw
    rep_t = len({r["checkpoint_id"] for r in rep if r["environment"] == "tau2"})
    rep_b = len({r["checkpoint_id"] for r in rep if r["environment"] == "bfcl"})
    hck = len({r["checkpoint_id"] for r in hosted})
    cck = len({r["checkpoint_id"] for r in ctrl})
    return [["Main study", f"{len(main):,}",
             f"U, N, L and PA with one run per checkpoint, model and condition: {len({r['model'] for r in main})} models on {tb} tau2 and BFCL checkpoints, "
             f"ten open-weight models on {aw} AppWorld checkpoints."],
            ["Retail and airline track", f"{len(ra):,}", f"U, N, L and PA on {len({r['checkpoint_id'] for r in ra})} checkpoints with five open-weight models."],
            ["Repeated runs", f"{len(rep):,}", f"U, N, L and PA on {rep_t} tau2 and {rep_b} BFCL checkpoints with a demonstrated fix, three repetitions per cell, open-weight models."],
            ["Three-sample hosted comparison", f"{len(hosted):,}",
             f"GPT-5.4-mini, GPT-5.5 and GPT-6.1-sol, all four conditions and three samples on the same {hck} checkpoints; {shared} of these runs are also the main-study runs of their cells."],
            ["Competence controls", f"{len(ctrl):,}",
             f"Additional exact-call and externally corrected-state continuations on {cck} BFCL checkpoints with ten models; matched U/PA and clean-start results provide comparisons."],
            ["Total", f"{total:,}", "Unique continuation job identifiers across the listed studies."]]


if __name__ == "__main__":
    show(rows())
