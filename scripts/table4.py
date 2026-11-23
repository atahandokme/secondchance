"""Table 4 (Appendix A.1): source episodes, candidates flagged by the mechanical screen, and checkpoints. No continuation outcome is read
at any stage.
  python scripts/table4.py"""
from common import checkpoints, load, show

ENV = ("tau2", "bfcl", "appworld")


def rows():
    ep = load("source_episodes")
    cks = [c for c in checkpoints().values() if c["split"] == "main"]
    f = lambda vals: [f"{v:,}" for v in vals] + [f"{sum(vals):,}"]  # noqa: E731
    out = [["Source episodes"] + f([sum(e["environment"] == env for e in ep) for env in ENV]),
           ["ended in task success"] + f([sum(e["environment"] == env and e["task_success"] for e in ep) for env in ENV]),
           ["Candidates"] + f([sum(e["candidates"] for e in ep if e["environment"] == env) for env in ENV]),
           ["Checkpoints"] + f([sum(c["environment"] == env for c in cks) for env in ENV]),
           ["distinct tasks"] + f([len({c["task_id"] for c in cks if c["environment"] == env}) for env in ENV])]
    return out


if __name__ == "__main__":
    show([["Stage", "tau2", "BFCL", "AppW.", "Total"]] + rows())
