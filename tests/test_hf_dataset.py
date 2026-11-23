"""The Hugging Face dataset holds exactly the rows shipped in this repository. Runs only when SECONDCHANCE_HF_DATASET is set to the hub id
or a local copy of the dataset (needs `pip install datasets`)."""
import json
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DS = os.environ.get("SECONDCHANCE_HF_DATASET")
pytestmark = pytest.mark.skipif(not DS, reason="set SECONDCHANCE_HF_DATASET to check the Hugging Face dataset")
PAIRS = [("continuations", s, f"results/{s}.jsonl") for s in ("main_study", "repeated", "hosted_three_sample", "retail_airline", "competence_controls")]
PAIRS += [("source_episodes", "train", "results/source_episodes.jsonl")]


@pytest.fixture(scope="module")
def cache(tmp_path_factory):
    """a fresh datasets cache, so the check always reads the current files"""
    return str(tmp_path_factory.mktemp("hf_cache"))


def jl(p):
    return [json.loads(l) for l in (ROOT / p).read_text().splitlines() if l.strip()]


@pytest.mark.parametrize("config,split,path", PAIRS)
def test_rows_identical(config, split, path, cache):
    from datasets import load_dataset
    hf = [dict(r) for r in load_dataset(DS, config, split=split, cache_dir=cache)]
    assert hf == jl(path)


def test_checkpoints_identical(cache):
    from datasets import load_dataset
    hf = {r["id"]: dict(r) for s in ("main", "supplementary") for r in load_dataset(DS, "checkpoints", split=s, cache_dir=cache)}
    repo = {r["id"]: r for r in jl("checkpoints/index.jsonl")}
    assert set(hf) == set(repo)
    for cid, r in repo.items():
        h = hf[cid]
        assert {k: h[k] for k in r} == r, cid
        d = ROOT / "checkpoints" / cid
        if r["environment"] == "appworld":
            assert h["visible_history"] is None and h["evaluation"] is None
        else:
            assert json.loads(h["visible_history"]) == json.loads((d / "history.json").read_text())
            assert json.loads(h["restore"]) == json.loads((d / "restore.json").read_text())
            meta = json.loads((d / "checkpoint.json").read_text())
            assert json.loads(h["evaluation"]) == meta["evaluation"] and json.loads(h["fixability_detail"]) == meta["fixability"]


def test_conditions_identical(cache):
    from datasets import load_dataset
    hf = {(r["checkpoint_id"], r["condition"]): r for r in load_dataset(DS, "conditions", split="train", cache_dir=cache)}
    n = 0
    for f in (ROOT / "conditions").glob("*.json"):
        d = json.loads(f.read_text())
        for c in ("N", "L", "PA"):
            x = d["conditions"][c]
            h = hf[(d["checkpoint_id"], c)]
            assert h["text"] == x["text"] and h["sha256"] == x["sha256"] and json.loads(h["clauses"]) == x["clauses"]
            n += 1
    assert n == len(hf)
