"""Build the Hugging Face dataset folder from the files shipped in this repository (results/, checkpoints/index.jsonl).
Writes Parquet files with an explicit schema under <out>/data/<config>/<split>.parquet; the dataset card (<out>/README.md) is kept
separately and lists the same configs. Needs `pip install datasets`.
  python scripts/build_hf_dataset.py <out folder>"""
import json
import sys
from pathlib import Path

from datasets import Dataset, Features, Value

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(sys.argv[1])

S, I, B = Value("string"), Value("int64"), Value("bool")
RUN = Features({"run_id": S, "study": S, "environment": S, "checkpoint_id": S, "task_id": S, "model": S, "model_name": S, "condition": S,
                "repetition": I, "status": S, "fixability": S, "error_kind": S, "task_success": B, "corrected_end": B, "corrected_ever": B,
                "n_regressions": I, "protected_state_intact": B, "complete_recovery": B, "recovery_class": S, "recovery_class_consent_first": S,
                "recovery_class_strict": S, "acknowledged": S, "further_changes": B, "semantic_review": S, "agent_calls": I,
                "agent_calls_before_extension": I, "input_tokens": I, "cached_input_tokens": I, "output_tokens": I, "simulated_user_turns": I,
                "simulated_user_calls": I, "first_correction_agent_calls": I, "first_correction_user_turns": I, "also_main_study_run": S,
                "harness_version": S})
CHECKPOINT = Features({"id": S, "environment": S, "split": S, "task_id": S, "source_model": S, "cut": I, "cut_unit": S, "error_kind": S, "mechanism": S,
                       "fixability": S, "fixability_evidence": S, "complete_recovery_route": S, "individually_reviewed": B, "competence_control": B,
                       # content (JSON strings; null for AppWorld, whose task data may be redistributed only in encrypted form)
                       "error": S, "visible_history": S, "restore": S, "state_file": S, "evaluation": S, "fixability_detail": S})
CONDITION = Features({"checkpoint_id": S, "condition": S, "text": S, "sha256": S, "clauses": S})
EPISODE = Features({"episode_id": S, "environment": S, "task_id": S, "source_model": S, "task_success": B, "candidates": I})


def jl(p):
    return [json.loads(l) for l in Path(p).read_text().splitlines() if l.strip()]


def write(rows, features, config, split):
    path = OUT / "data" / config / f"{split}.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    assert list(rows[0]) == list(features), (config, split)
    Dataset.from_list(rows, features=features).to_parquet(str(path))
    print(f"{config}/{split}: {len(rows)} rows")


def content(c):
    d = ROOT / "checkpoints" / c["id"]
    meta = json.loads((d / "checkpoint.json").read_text())
    has = (d / "history.json").exists()
    dump = lambda x: None if x is None else json.dumps(x, ensure_ascii=False)  # noqa: E731
    return {**c, "error": dump(meta.get("error")), "visible_history": (d / "history.json").read_text() if has else None,
            "restore": (d / "restore.json").read_text() if has else None,
            "state_file": f"checkpoints/{c['id']}/state.json.gz" if (d / "state.json.gz").exists() else None,
            "evaluation": dump(meta.get("evaluation")), "fixability_detail": dump(meta.get("fixability") if isinstance(meta.get("fixability"), dict) else None)}


cks = [content(c) for c in jl(ROOT / "checkpoints" / "index.jsonl")]
for split in ("main", "supplementary"):
    write([c for c in cks if c["split"] == split], CHECKPOINT, "checkpoints", split)
for study in ("main_study", "repeated", "hosted_three_sample", "retail_airline", "competence_controls"):
    write(jl(ROOT / "results" / f"{study}.jsonl"), RUN, "continuations", study)
write(jl(ROOT / "results" / "source_episodes.jsonl"), EPISODE, "source_episodes", "train")
conds = []
for f in sorted((ROOT / "conditions").glob("*.json")):
    d = json.loads(f.read_text())
    for c in ("N", "L", "PA"):
        x = d["conditions"][c]
        conds.append({"checkpoint_id": d["checkpoint_id"], "condition": c, "text": x["text"], "sha256": x["sha256"], "clauses": json.dumps(x["clauses"], ensure_ascii=False)})
write(conds, CONDITION, "conditions", "train")
