"""Stage 2 (the semantic review) reproduces the released classes of reviewed runs from the judge's recorded replies (no model is called).

For each fixture run (its record, with the checkpoint's database from the shipped state): stage 1 is scored from the record; every
packet the review builds must be byte-identical to the packet the judge saw in the evaluation (sha256), the agent's policy must be the
one the judge saw, the recorded replies are validated by the package's own validators, and the three classes must equal the released ones. The fixture covers the retail check, other writes, the consent question
asked again, unfinished work by transfer and by the judge's answer, the goal settled by the record, and a rejection.
Needs `pip install -e .[tau2]` and the tau2-bench data (`secondchance setup tau2`); skipped otherwise."""
import json
from pathlib import Path

import pytest

FX = json.loads((Path(__file__).resolve().parent / "fixtures" / "reviewed_runs.json").read_text())
CLS = {"ACCEPTED_COMPLETE_REPAIR": "complete_recovery", "ACCEPTED_CORRECTION_ONLY": "correction_only", "REJECTED": "rejected", "HELD_UNCERTAIN": "held"}


class RecordedJudge:
    """answers each question with the evaluation's recorded replies, after checking the package sends the judge the same packet"""

    def __init__(self, fx):
        self.fx, self.asked = fx, []

    def ask(self, question, pk, policy=None):
        from secondchance.review import judge as J
        self.asked.append(question)
        assert question in self.fx["judge_replies"], f"{question} was not asked in the evaluation"
        if question != "unfinished_work":
            assert J.sha(J.packet_text(pk)) == self.fx["packet_sha256"][question], f"{question}: packet differs from the one the judge saw"
            assert J.sha(policy or "") == self.fx["policy_sha256"], f"{question}: policy differs from the one the judge saw"
        return J.from_replies(question, pk, self.fx["judge_replies"][question])


@pytest.mark.parametrize("fx", FX, ids=lambda f: f["case"])
def test_review_reproduces_released_classes(fx):
    pytest.importorskip("tau2")
    from secondchance.setup_env import data_dir
    if not data_dir():
        pytest.skip("tau2-bench data missing: run `secondchance setup tau2`")
    from secondchance.data import Checkpoint
    from secondchance.review import pipeline as PL
    from secondchance.scoring import score as S
    ck = Checkpoint(fx["checkpoint_id"])
    rec = dict(fx["record"], checkpoint_db=ck.state())  # the database at the checkpoint, as every run record carries it
    st1 = S.score_tau2(rec, ck)
    assert str(st1["stage1"]).startswith("CANDIDATE")
    judge = RecordedJudge(fx)
    out = PL.review(rec, ck, st1, judge, run_key=None, condition=fx["condition"], rid=fx["review_id"])
    assert J_sha(out["packet"]) == fx["packet_sha256"]["recovery"]
    got = {"recovery_class": CLS[out["complete_recovery_class"]], "recovery_class_consent_first": CLS[out["consent_first_class"]],
           "recovery_class_strict": CLS[out["strict_class"]]}
    assert got == fx["expected"]


def J_sha(pk):
    from secondchance.review import judge as J
    return J.sha(J.packet_text(pk))


def test_released_results_carry_these_runs():
    from secondchance.data import home
    rows = {}
    for f in ("main_study", "repeated", "hosted_three_sample", "retail_airline"):
        for line in (home() / "results" / f"{f}.jsonl").read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                rows[r["run_id"]] = r
    for fx in FX:
        r = rows[fx["run_id"]]
        assert {k: r[k] for k in fx["expected"]} == fx["expected"]
        assert r["semantic_review"]
