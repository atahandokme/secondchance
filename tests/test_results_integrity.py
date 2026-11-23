"""Integrity of the shipped run files: counts, identifiers, one schema, and nothing machine-specific."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import common  # noqa: E402

COUNTS = {"main_study": 5760, "repeated": 3360, "hosted_three_sample": 1332, "retail_airline": 480, "competence_controls": 360}


def test_counts_and_unique_ids():
    seen = set()
    for study, n in COUNTS.items():
        rows = common.load(study)
        assert len(rows) == n, study
        ids = [r["run_id"] for r in rows]
        assert len(set(ids)) == n, study
        seen |= set(ids)
    hosted = common.load("hosted_three_sample")
    shared = [r["also_main_study_run"] for r in hosted if r["also_main_study_run"]]
    assert len(shared) == 296 and set(shared) <= {r["run_id"] for r in common.load("main_study")}


def test_total_unique_continuations():
    hosted = common.load("hosted_three_sample")
    shared = sum(1 for r in hosted if r["also_main_study_run"])
    assert sum(COUNTS.values()) - shared == 10996


def test_shared_runs_identical():
    main = {r["run_id"]: r for r in common.load("main_study")}
    fields = ("task_success", "corrected_end", "corrected_ever", "n_regressions", "complete_recovery", "recovery_class", "agent_calls")
    for r in common.load("hosted_three_sample"):
        if r["also_main_study_run"]:
            m = main[r["also_main_study_run"]]
            assert all(r[f] == m[f] for f in fields), r["run_id"]


def test_one_schema():
    cols = None
    for study in COUNTS:
        for r in common.load(study):
            cols = cols or list(r)
            assert list(r) == cols, study


def test_main_study_status():
    from collections import Counter
    st = Counter(r["status"] for r in common.load("main_study"))
    assert st == {"scored": 5685, "no_outcome": 63, "protocol_excluded": 12}


def test_checkpoints():
    cks = common.checkpoints()
    assert sum(c["split"] == "main" for c in cks.values()) == 129 and sum(c["split"] == "supplementary" for c in cks.values()) == 24
    for study in COUNTS:
        assert {r["checkpoint_id"] for r in common.load(study)} <= set(cks)


def test_no_machine_specific_content():
    for f in list((ROOT / "results").glob("*.jsonl")) + [ROOT / "checkpoints" / "index.jsonl"]:
        text = f.read_text()
        for bad in ("/home/", "/nethome/", "/usr/", "127.0.0.1", "sk-"):
            assert bad not in text, (f.name, bad)
