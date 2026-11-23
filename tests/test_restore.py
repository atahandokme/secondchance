"""Replay verification on every shipped checkpoint: a fresh environment plus the replay of the history's executed calls reproduces the
recorded tool responses and state hashes. Needs `pip install -e .[tau2,bfcl]` and TAU2_DATA_DIR (tau2-bench data at the pinned commit);
skipped otherwise. No model is called."""
import os

import pytest

from secondchance.data import Checkpoint, index

IDX = index()
TAU2 = sorted(c for c, x in IDX.items() if x["environment"] in ("tau2", "retail", "airline"))
BFCL = sorted(c for c, x in IDX.items() if x["environment"] == "bfcl")


@pytest.mark.parametrize("cid", TAU2)
def test_tau2_restore(cid):
    pytest.importorskip("tau2")
    if not os.environ.get("TAU2_DATA_DIR"):
        pytest.skip("set TAU2_DATA_DIR to the pinned tau2-bench data/ folder")
    from secondchance.envs import tau2_env
    rep = tau2_env.restore(Checkpoint(cid))[3]
    assert rep["ok"], rep


@pytest.mark.parametrize("cid", BFCL)
def test_bfcl_restore(cid):
    pytest.importorskip("bfcl_eval")
    from secondchance.envs import bfcl_env
    rep = bfcl_env.restore_checkpoint(Checkpoint(cid))[2]
    assert rep["ok"], rep
