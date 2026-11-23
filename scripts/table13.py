"""Table 13 (Appendix D): supporting studies, counts of runs with task success / corrected at the end / complete recovery per condition.
Retail and airline: five open-weight models, one greedy run per condition (corrections are counted on the runs whose checkpoint has a
field-level target). Three samples per cell: the tau2 and BFCL checkpoints with a demonstrated fix, repeated runs plus the hosted models.
  python scripts/table13.py"""
from common import CONDS, NAMES, load, show, yes

ORDER = {"tau2": ("gemma-4-31b", "gpt-oss-120b", "llama-3.3-70b", "qwen3-235b", "qwen3-32b", "gpt-5.4-mini", "gpt-5.5", "gpt-6.1-sol"),
         "bfcl": ("gemma-4-31b", "gpt-oss-120b", "gpt-oss-20b", "llama-3.1-8b", "llama-3.3-70b", "mistral-small-3.2", "qwen3.5-35b-a3b", "qwen3-235b",
                  "qwen3-32b", "qwen3-4b", "gpt-5.4-mini", "gpt-5.5", "gpt-6.1-sol")}


def cell(x):
    return "/".join(str(sum(yes(r, f) for r in x)) for f in ("task_success", "corrected_end", "complete_recovery"))


def line(name, runs):
    n = {c: sum(r["condition"] == c for r in runs) for c in CONDS}
    assert len(set(n.values())) == 1, name
    return [name, str(n["U"])] + [cell([r for r in runs if r["condition"] == c]) for c in CONDS]


def rows():
    out = []
    ra = [r for r in load("retail_airline") if r["status"] != "protocol_excluded"]
    for env, name in (("retail", "Retail"), ("airline", "Airline")):
        sel = [r for r in ra if r["environment"] == env]
        out.append(line(f"{name} ({len({r['model'] for r in sel})})", sel))
    three = load("repeated") + load("hosted_three_sample")
    for env, label in (("tau2", "tau2"), ("bfcl", "BFCL")):
        sel = [r for r in three if r["environment"] == env]
        out.append([f"{label}: {len({r['checkpoint_id'] for r in sel})} checkpoints from {len({r['task_id'] for r in sel})} tasks"])
        assert {r["model"] for r in sel} == set(ORDER[env])
        for m in ORDER[env]:
            out.append(line(NAMES[m], [r for r in sel if r["model"] == m]))
    return out


if __name__ == "__main__":
    show(rows())
