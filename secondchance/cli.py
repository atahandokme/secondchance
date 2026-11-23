"""secondchance: command-line entry points.

  secondchance setup tau2                                                 install tau2-bench at the pinned commit and its data
  secondchance list        [--env tau2|bfcl|retail|airline] [--quickstart]
  secondchance verify      [--checkpoints quickstart|all|<id,id>]         restore every checkpoint and check it reproduces the recorded state
  secondchance run         --model M --api-base URL [--checkpoints quickstart|all|<id,id>] [--conditions U,N,L,PA] --out DIR
                           [--user-model M2 --user-api-base URL2]          tau2: the user simulator (default gpt-4.1-2025-04-14)
  secondchance score       --runs DIR [--out scores.jsonl]                stage 1 of every run record in DIR (BFCL: final)
                           [--judge-url URL --judge-model NAME]           + stage 2 for tau2/retail/airline candidates: the semantic review
                                                                          by the pinned judge (reviews saved next to --out)
  secondchance scorecard   --scores scores.jsonl                          rates per condition, as in the paper's Table 3
  secondchance reproduce   [--source repo|hf:<dataset>]                    every table and Figure 2 of the paper from the shipped results"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

from secondchance import __version__
from secondchance.data import Checkpoint, home, index

QUICKSTART = "quickstart.json"


def select(spec, env=None):
    idx = index()
    if spec in (None, "quickstart"):
        ids = json.loads((home() / "checkpoints" / QUICKSTART).read_text())["checkpoints"]
    elif spec == "all":
        ids = sorted(c for c, x in idx.items() if x["environment"] != "appworld")
    else:
        ids = spec.split(",")
    return [c for c in ids if env is None or idx[c]["environment"] == env]


def cmd_list(a):
    idx = index()
    ids = select("quickstart") if a.quickstart else sorted(idx)
    for c in ids:
        x = idx[c]
        if a.env and x["environment"] != a.env:
            continue
        print(f"{c:14s} {x['environment']:9s} {x['task_id'][:60]:60s} fixability={x['fixability']}")


def cmd_verify(a):
    from secondchance.envs import bfcl_env, tau2_env
    bad = 0
    for c in select(a.checkpoints):
        ck = Checkpoint(c)
        rep = bfcl_env.restore_checkpoint(ck)[2] if ck.environment == "bfcl" else tau2_env.restore(ck)[3]
        bad += not rep["ok"]
        print(f"{c:14s} {'OK' if rep['ok'] else 'MISMATCH'}")
    print(f"{'all checkpoints restore exactly' if not bad else str(bad) + ' checkpoint(s) do not restore'}")
    return 1 if bad else 0


def cmd_run(a):
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    conds = a.conditions.split(",")
    replay = {}
    if a.replay:  # recorded runs instead of a model (tests and demonstrations; no model is called)
        replay = {(f["checkpoint_id"], f["condition"]): f for f in json.loads(Path(a.replay).read_text())}
    for c in select(a.checkpoints):
        ck = Checkpoint(c)
        for cond in conds:
            f = out / f"{c}__{cond}__s{a.seed}.json"
            if f.exists():
                continue
            fx = replay.get((c, cond)) if a.replay else None
            if a.replay and fx is None:
                continue
            if ck.environment == "bfcl":
                from secondchance.envs import bfcl_run
                comp = bfcl_run.replay_completion({"messages": [{}] * ck.meta["cut"] + fx["messages_after_cut"]}, ck.meta["cut"]) if fx else None
                rec = bfcl_run.run(ck, cond, a.model, api_base=a.api_base, temperature=a.temperature, seed=a.seed,
                                   single_tool_call=a.single_tool_call or bool(fx and fx["single_tool_call"]), completion=comp)
            else:
                from secondchance.envs import tau2_run
                comp = tau2_run.replay_completion(fx, a.model, a.user_model) if fx else None
                rec = tau2_run.run(ck, cond, a.model, {**({"api_base": a.api_base} if a.api_base else {}), "temperature": a.temperature},
                                   a.user_model, {**({"api_base": a.user_api_base} if a.user_api_base else {})}, seed=a.seed, completion=comp)
            rec["secondchance_version"] = __version__
            f.write_text(json.dumps(rec, default=str))
            print(f"{c} {cond}: {rec.get('status')}")


def cmd_score(a):
    from secondchance.scoring import acceptance_rules as AR
    from secondchance.scoring import score as S
    judge = None
    if a.judge_url:
        from secondchance.review import judge as J
        judge = J.Judge(a.judge_url, a.judge_model or J.MODEL)
        rdir = Path(a.out or "scores.jsonl").with_suffix(".reviews")
        rdir.mkdir(parents=True, exist_ok=True)
    rows = []
    for f in sorted(Path(a.runs).glob("*.json")):
        rec = json.loads(f.read_text())
        ck = Checkpoint(rec["checkpoint_id"])
        row = {"file": f.name, "checkpoint_id": ck.id, "environment": ck.environment, "condition": rec["cond"], "status": rec.get("status")}
        if rec.get("status") in ("INFRASTRUCTURE_FAILURE", "CONTEXT_STOP") and not rec.get("continuation") and not rec.get("executed_calls"):
            row["no_outcome"] = True
        else:
            out = S.score_bfcl(rec, ck) if ck.environment == "bfcl" else S.score_tau2(rec, ck)
            row.update({k: out.get(k) for k in ("corrected_end", "corrected_ever", "n_regressions", "protected_state_intact", "task_success", "stage1", "recovery_class")})
            if ck.environment != "bfcl":
                no_target = ck.environment in ("retail", "airline") and not ck.meta["scoring_inputs"]["effects"]
                if no_target:
                    row["recovery_class"] = "NOT_APPLICABLE"  # no field-level effect: correction is not scored
                elif not str(out["stage1"]).startswith("CANDIDATE"):
                    row["recovery_class"] = AR.decide(out["components"], None)[0]
                elif judge is not None:
                    from secondchance.review import pipeline as PL
                    rv = PL.review(rec, ck, out, judge, run_key=f.stem, condition=rec["cond"])
                    row.update(recovery_class=rv["complete_recovery_class"], recovery_class_consent_first=rv["consent_first_class"],
                               recovery_class_strict=rv["strict_class"], review_id=rv["review_id"])
                    (rdir / f"{f.stem}.review.json").write_text(json.dumps(rv, indent=1, default=str))
        rows.append(row)
    text = "".join(json.dumps(r) + "\n" for r in rows)
    if a.out:
        Path(a.out).write_text(text)
    else:
        sys.stdout.write(text)


def cmd_scorecard(a):
    rows = [json.loads(l) for l in Path(a.scores).read_text().splitlines() if l.strip()]
    by = defaultdict(list)
    for r in rows:
        by[r["condition"]].append(r)
    rate = lambda k, n: f"{k / n:.2f}".lstrip("0") if n else "--"  # noqa: E731
    reviewed = any("review_id" in r for r in rows)
    print("cond   n   corrected  task  complete  " + ("" if reviewed else "(tau2/retail/airline: stage-1 candidates, not reviewed)"))
    for c in ("U", "N", "L", "PA"):
        x = by.get(c, [])
        n = len(x)
        cor = sum(r.get("corrected_end") is True for r in x)
        task = sum(r.get("task_success") is True for r in x)
        comp = sum(r.get("recovery_class") == "ACCEPTED_COMPLETE_REPAIR" for r in x)
        cand = sum(str(r.get("stage1")).startswith("CANDIDATE_COMPLETE") and "review_id" not in r for r in x if r["environment"] != "bfcl")
        print(f"{c:4s} {n:4d}   {rate(cor, n):>8s}  {rate(task, n):>5s}  {rate(comp, n):>8s}" + (f"  (+{cand} unreviewed candidates)" if cand else ""))


def cmd_setup(a):
    from secondchance import setup_env
    if a.what == "tau2":
        setup_env.tau2(a.dir)


def cmd_reproduce(a):
    import os
    env = dict(os.environ)
    if a.source and a.source != "repo":
        env["SECONDCHANCE_DATA"] = a.source
    return subprocess.call([sys.executable, str(home() / "scripts" / "verify.py")], env=env)


def main(argv=None):
    p = argparse.ArgumentParser(prog="secondchance", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("list"); s.add_argument("--env"); s.add_argument("--quickstart", action="store_true"); s.set_defaults(f=cmd_list)
    s = sub.add_parser("verify"); s.add_argument("--checkpoints", default="all"); s.set_defaults(f=cmd_verify)
    s = sub.add_parser("run")
    s.add_argument("--model", required=True, help='LiteLLM model string, e.g. "openai/<served model name>" for an OpenAI-compatible endpoint')
    s.add_argument("--api-base", default=None); s.add_argument("--checkpoints", default="quickstart"); s.add_argument("--conditions", default="U,N,L,PA")
    s.add_argument("--user-model", default="gpt-4.1-2025-04-14"); s.add_argument("--user-api-base", default=None)
    s.add_argument("--temperature", type=float, default=0.0); s.add_argument("--seed", type=int, default=0)
    s.add_argument("--single-tool-call", action="store_true", help="BFCL: send one tool call per assistant message (Llama-3 chat templates)")
    s.add_argument("--replay", help="a JSON file of recorded runs to feed back instead of calling a model (tests/fixtures/recorded_runs.json)")
    s.add_argument("--out", required=True); s.set_defaults(f=cmd_run)
    s = sub.add_parser("score"); s.add_argument("--runs", required=True); s.add_argument("--out")
    s.add_argument("--judge-url", help="OpenAI-compatible endpoint serving the pinned judge (Qwen/Qwen3-235B-A22B-GPTQ-Int4): runs stage 2")
    s.add_argument("--judge-model", help="the judge's served model name (default: the pinned model id)"); s.set_defaults(f=cmd_score)
    s = sub.add_parser("scorecard"); s.add_argument("--scores", required=True); s.set_defaults(f=cmd_scorecard)
    s = sub.add_parser("reproduce"); s.add_argument("--source", default="repo"); s.set_defaults(f=cmd_reproduce)
    s = sub.add_parser("setup"); s.add_argument("what", choices=["tau2"]); s.add_argument("--dir"); s.set_defaults(f=cmd_setup)
    a = p.parse_args(argv)
    return a.f(a) or 0


if __name__ == "__main__":
    sys.exit(main())
