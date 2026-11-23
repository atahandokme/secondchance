"""Shared helpers for the table and figure scripts. Every script reads only the shipped files under results/ and checkpoints/.

Conventions used throughout the paper:
  * a run without a model outcome (status "no_outcome") stays in every denominator and counts as not corrected and not recovered;
  * runs in protocol-excluded cells (status "protocol_excluded") are left out of every count;
  * rates are printed on a 0 to 1 scale with two decimals and no leading zero (".27", "1.00");
  * 95% intervals are percentile intervals from 2,000 cluster-bootstrap resamples of source tasks with random.Random(0).
"""
import json
import os
import random
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONDS = ("U", "N", "L", "PA")
ENVS = ("tau2", "bfcl", "appworld")
# model order of Table 3 (and of every per-model table in the appendix that follows it)
MODELS = ("gpt-6.1-sol", "gemma-4-31b", "qwen3.5-35b-a3b", "gpt-5.4-mini", "gpt-oss-120b", "mistral-small-3.2", "gpt-oss-20b", "llama-3.3-70b",
          "qwen3-235b", "qwen3-4b", "llama-3.1-8b", "qwen3-32b")
NAMES = {"gpt-6.1-sol": "GPT-6.1-sol", "gpt-5.4-mini": "GPT-5.4-mini", "gpt-5.5": "GPT-5.5", "gemma-4-31b": "Gemma-4-31B", "qwen3.5-35b-a3b": "Qwen3.5-35B-A3B",
         "gpt-oss-120b": "gpt-oss-120b", "mistral-small-3.2": "Mistral-Small-3.2", "gpt-oss-20b": "gpt-oss-20b", "llama-3.3-70b": "Llama-3.3-70B",
         "qwen3-235b": "Qwen3-235B", "qwen3-4b": "Qwen3-4B", "llama-3.1-8b": "Llama-3.1-8B", "qwen3-32b": "Qwen3-32B"}
HOSTED = ("gpt-6.1-sol", "gpt-5.4-mini", "gpt-5.5")
ENV_NAME = {"tau2": "tau2", "bfcl": "BFCL", "appworld": "AppWorld"}


# Where the rows come from. Unset: the files shipped in this repository (results/, checkpoints/index.jsonl).
# SECONDCHANCE_DATA=hf:<hub id or local dataset folder>: the Hugging Face dataset (needs `pip install datasets`).
SOURCE = os.environ.get("SECONDCHANCE_DATA", "")
HF_SPLIT = {"main_study": ("continuations", "main_study"), "repeated": ("continuations", "repeated"),
            "hosted_three_sample": ("continuations", "hosted_three_sample"), "retail_airline": ("continuations", "retail_airline"),
            "competence_controls": ("continuations", "competence_controls"), "source_episodes": ("source_episodes", "train")}
_cache = {}


def _hf(config, split):
    import tempfile
    from datasets import load_dataset
    global _HF_CACHE
    if "_HF_CACHE" not in globals():
        _HF_CACHE = tempfile.mkdtemp(prefix="secondchance_hf_")  # fresh cache: always the dataset's current files
    return [dict(r) for r in load_dataset(SOURCE[3:], config, split=split, cache_dir=_HF_CACHE)]


def load(study):
    """the run rows of one study: main_study, repeated, hosted_three_sample, retail_airline, competence_controls; or source_episodes"""
    if study not in _cache:
        if SOURCE.startswith("hf:"):
            _cache[study] = _hf(*HF_SPLIT[study])
        else:
            _cache[study] = [json.loads(l) for l in (ROOT / "results" / f"{study}.jsonl").read_text().splitlines() if l.strip()]
    return _cache[study]


def checkpoints():
    if "checkpoints" not in _cache:
        if SOURCE.startswith("hf:"):
            rows = _hf("checkpoints", "main") + _hf("checkpoints", "supplementary")
        else:
            rows = [json.loads(l) for l in (ROOT / "checkpoints" / "index.jsonl").read_text().splitlines() if l.strip()]
        _cache["checkpoints"] = {c["id"]: c for c in rows}
    return _cache["checkpoints"]


def counted(rows):
    """runs that enter denominators: everything except protocol-excluded cells"""
    return [r for r in rows if r["status"] != "protocol_excluded"]


def yes(r, field):
    return r["status"] == "scored" and r.get(field) is True


def rate(k, n):
    if not n:
        return "--"
    s = f"{k / n:.2f}"
    return s[1:] if s.startswith("0") else s


def rate_half_up(k, n):
    """rates as printed in the appendix scorecard (Table 11): exact halves round up (9/72 = .125 prints as .13)"""
    if not n:
        return "--"
    p = int(100 * k / n + 0.5)
    return "1.00" if p == 100 else f".{p:02d}"


def task_cluster(r):
    """the bootstrap cluster of a run: its source task (retail and airline: its checkpoint, as in the paper)"""
    return r["checkpoint_id"] if r["environment"] in ("retail", "airline") else r["task_id"]


def paired_pp(cells, a, b, field, rng=None):
    """cells: {cluster key tuple (task, ...): {cond: 0/1}}; difference a-b in percentage points with a source-task bootstrap interval.
    rng: a fresh random.Random(0) unless the caller shares one across comparisons (as the paper's three-sample rows do)."""
    rng = rng or random.Random(0)
    by = defaultdict(list)
    for k, v in cells.items():
        by[k[0]].append(v[a][field] - v[b][field])
    tasks = sorted(by)
    allv = [x for t in tasks for x in by[t]]
    est = 100 * sum(allv) / len(allv)
    bs = []
    for _ in range(2000):
        xs = [x for t in (rng.choice(tasks) for _ in tasks) for x in by[t]]
        bs.append(100 * sum(xs) / len(xs))
    bs.sort()
    return est, bs[49], bs[1949], len(allv)


def fmt_pp(est, lo, hi):
    """'+10.0 [5.7,14.9]' as printed in the paper"""
    def one(x, sign):
        x = round(x, 1)
        s = f"{x:.1f}" if x != int(x) or sign else f"{x:g}"
        if sign and x > 0:
            s = "+" + s
        return s
    e = round(est, 1)
    head = "0.0" if e == 0 else (f"+{e:.1f}" if e > 0 else f"{e:.1f}")
    lo_, hi_ = round(lo, 1), round(hi, 1)
    b = lambda x: (f"{x:g}" if x == int(x) else f"{x:.1f}")  # noqa: E731
    return f"{head} [{b(lo_)},{b(hi_)}]"


def median(xs):
    return statistics.median(xs)


def quartiles(xs):
    """median and the first and third quartiles as in the paper: the value at rank round(q * (n - 1)) of the sorted list"""
    xs = sorted(xs)
    p = lambda f: xs[min(len(xs) - 1, int(round(f * (len(xs) - 1))))]  # noqa: E731
    return statistics.median(xs), p(0.25), p(0.75)


def boot_median_diff(pairs, B=2000, seed=0):
    """pairs: [(cluster, difference)]; median difference and source-task cluster bootstrap 95% interval"""
    by = defaultdict(list)
    for t, d in pairs:
        by[t].append(d)
    tasks = sorted(by)
    rng = random.Random(seed)
    meds = []
    for _ in range(B):
        xs = [d for t in (rng.choice(tasks) for _ in tasks) for d in by[t]]
        meds.append(statistics.median(xs))
    meds.sort()
    return statistics.median([d for _, d in pairs]), meds[int(0.025 * B)], meds[int(0.975 * B) - 1]


def show(rows):
    w = [max(len(r[i]) if i < len(r) else 0 for r in rows) for i in range(max(len(r) for r in rows))]
    for r in rows:
        print("  ".join(c.ljust(w[i]) for i, c in enumerate(r)))


def all_unique_runs():
    """every continuation once: the main study, the supporting studies and the retail/airline track; a hosted three-sample run that is
    also the main-study run of its cell is counted once (it appears in both files with the same outcomes)"""
    main = load("main_study")
    hosted = load("hosted_three_sample")
    dup = {r["also_main_study_run"] for r in hosted if r.get("also_main_study_run")}
    return [r for r in main if r["run_id"] not in dup] + hosted + load("repeated") + load("retail_airline")
