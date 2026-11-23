"""The runners and the scorer reproduce recorded runs: the recorded agent and simulated-user turns are fed back instead of a model
(no model is called), and the new run's messages and scored outcome must equal the recorded run and the released results.
Needs `pip install -e .[tau2,bfcl]` and the tau2-bench data (`secondchance setup tau2`); skipped otherwise."""
import json
import re
from pathlib import Path

import pytest

FX = json.loads((Path(__file__).resolve().parent / "fixtures" / "recorded_runs.json").read_text())
TIM = re.compile(r"\[Timing: retrieval=\d+ms, reranking=\d+ms, total=\d+ms\]")  # banking search output carries wall-clock timing


def key(ms):
    return [(m["role"], TIM.sub("", str(m.get("content"))), [(t["name"], t["arguments"]) for t in m.get("tool_calls") or []]) for m in ms]


@pytest.mark.parametrize("fx", [f for f in FX if f["environment"] == "tau2"], ids=lambda f: f["run_id"])
def test_tau2_replay(fx):
    pytest.importorskip("tau2")
    from secondchance.setup_env import data_dir
    if not data_dir():
        pytest.skip("tau2-bench data missing: run `secondchance setup tau2`")
    from secondchance.data import Checkpoint
    from secondchance.envs import tau2_run
    from secondchance.scoring import score as S
    ck = Checkpoint(fx["checkpoint_id"])
    ag, us = "openai/replay-agent", "openai/replay-user"
    new = tau2_run.run(ck, fx["condition"], ag, {}, us, {}, seed=0, completion=tau2_run.replay_completion(fx, ag, us))
    assert key(new["continuation"]) == key(fx["continuation"])
    out = S.score_tau2(new, ck)
    assert {k: out[k] for k in fx["expected"]} == fx["expected"]


@pytest.mark.parametrize("fx", [f for f in FX if f["environment"] == "bfcl"], ids=lambda f: f["run_id"])
def test_bfcl_replay(fx):
    pytest.importorskip("bfcl_eval")
    from secondchance.data import Checkpoint
    from secondchance.envs import bfcl_run
    from secondchance.scoring import score as S
    ck = Checkpoint(fx["checkpoint_id"])
    rec = {"messages": [{}] * ck.meta["cut"] + fx["messages_after_cut"]}
    new = bfcl_run.run(ck, fx["condition"], "openai/replay", completion=bfcl_run.replay_completion(rec, ck.meta["cut"]), single_tool_call=fx["single_tool_call"])
    out = S.score_bfcl(new, ck)
    want = {k: v for k, v in fx["expected"].items() if k != "recovery_class"}
    assert {k: out[k] for k in want} == want
    names = {"complete_recovery": "ACCEPTED_COMPLETE_REPAIR", "correction_only": "ACCEPTED_CORRECTION_ONLY", "rejected": "REJECTED", "held": "HELD_UNCERTAIN"}
    assert out["recovery_class"] == names[fx["expected"]["recovery_class"]]
