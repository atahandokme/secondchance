"""The four assistance conditions as shipped baselines: per model, environment and condition, the main study's run count and the rates of
correction, task success and complete recovery (and the same on the checkpoints with a demonstrated fix). A new method evaluated on the
same checkpoints compares against these rows. Reads results/main_study.jsonl; writes baselines/main_study.jsonl.
  python baselines/make_baselines.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from common import CONDS, MODELS, NAMES, counted, load, yes  # noqa: E402

rows = []
runs = counted(load("main_study"))
for scope in ("all", "demonstrated"):
    for env in ("tau2", "bfcl", "appworld"):
        for m in MODELS:
            for c in CONDS:
                x = [r for r in runs if r["environment"] == env and r["model"] == m and r["condition"] == c and (scope == "all" or r["fixability"] == "demonstrated")]
                if not x:
                    continue
                n = len(x)
                rows.append({"checkpoints": scope, "environment": env, "model": m, "model_name": NAMES[m], "condition": c, "runs": n,
                             "corrected": sum(yes(r, "corrected_end") for r in x), "task_success": sum(yes(r, "task_success") for r in x),
                             "complete_recovery": sum(yes(r, "complete_recovery") for r in x),
                             "corrected_rate": round(sum(yes(r, "corrected_end") for r in x) / n, 4),
                             "complete_recovery_rate": round(sum(yes(r, "complete_recovery") for r in x) / n, 4)})
(ROOT / "baselines" / "main_study.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
print(len(rows), "baseline rows")
