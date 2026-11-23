"""Table 17 (Appendix F.2): work from the checkpoint to termination on matched cells (a cell has both a U and a PA run with work records).
U and PA: median [first, third quartile] over all runs; PA-U: median paired difference [95% source-task bootstrap interval, 2,000
resamples, random.Random(0)]. Input tokens include the restored history resent with each request. Open: open-weight models.
  python scripts/table17.py"""
from collections import defaultdict

from common import boot_median_diff, load, quartiles, show, task_cluster

FIRST_FIVE = ("gemma-4-31b", "gpt-oss-120b", "llama-3.3-70b", "qwen3-235b", "qwen3-32b")
OPEN = FIRST_FIVE + ("gpt-oss-20b", "llama-3.1-8b", "mistral-small-3.2", "qwen3.5-35b-a3b", "qwen3-4b")


def g(x):
    return f"{x:g}"


def q(xs, k=1):
    m, lo, hi = quartiles([x for x in xs if x is not None])
    f = (lambda x: f"{x / k:.0f}") if k > 1 else g
    return f"{f(m)} [{f(lo)}, {f(hi)}]"


def dq(pairs, k=1, dec=0):
    m, lo, hi = boot_median_diff(pairs)
    f = (lambda x: f"{x / k:.1f}") if dec else g
    return ("+" if m > 0 else "") + f"{f(m)} [{f(lo)}, {f(hi)}]"


def setting(label, runs, key, users):
    idx = defaultdict(dict)
    for r in runs:
        if r["condition"] in ("U", "PA") and r["agent_calls"] is not None and r["status"] != "protocol_excluded":
            idx[key(r)][r["condition"]] = r
    M = [v for v in idx.values() if "U" in v and "PA" in v]
    W = lambda v, f: v[f]  # noqa: E731
    pairs = lambda f: [(task_cluster(v["U"]), W(v["PA"], f) - W(v["U"], f)) for v in M if W(v["U"], f) is not None and W(v["PA"], f) is not None]  # noqa: E731
    row = [label, str(len(M))]
    row += [q([W(v["U"], "agent_calls") for v in M]), q([W(v["PA"], "agent_calls") for v in M]), dq(pairs("agent_calls"))]
    row += [q([W(v["U"], "input_tokens") for v in M], 1000), q([W(v["PA"], "input_tokens") for v in M], 1000), dq(pairs("input_tokens"), 1000, 1)]
    row.append(dq(pairs("simulated_user_turns")) if users else "N/A")
    return row


def rows():
    main = load("main_study")
    ck_model = lambda r: (r["checkpoint_id"], r["model"])  # noqa: E731
    out = [setting("tau2 (5 open)", [r for r in main if r["environment"] == "tau2" and r["model"] in FIRST_FIVE], ck_model, True),
           setting("BFCL (10 open)", [r for r in main if r["environment"] == "bfcl" and r["model"] in OPEN], ck_model, False),
           setting("AppWorld (10 open)", [r for r in main if r["environment"] == "appworld" and r["model"] in OPEN], ck_model, False)]
    hosted = load("hosted_three_sample")
    for m, name in (("gpt-5.4-mini", "GPT-5.4-mini"), ("gpt-5.5", "GPT-5.5"), ("gpt-6.1-sol", "GPT-6.1-sol")):
        out.append(setting(f"tau2, {name}", [r for r in hosted if r["environment"] == "tau2" and r["model"] == m],
                           lambda r: (r["checkpoint_id"], r["model"], r["repetition"]), True))
    return out


if __name__ == "__main__":
    show(rows())
