"""The shipped checkpoint folders and assistance texts: complete, consistent with the index, hashes intact, nothing machine-specific,
and no AppWorld-derived content (AppWorld permits redistribution of its task data only in encrypted form)."""
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = {c["id"]: c for c in (json.loads(l) for l in (ROOT / "checkpoints" / "index.jsonl").read_text().splitlines() if l.strip())}


def test_every_checkpoint_has_its_folder():
    for cid, c in INDEX.items():
        d = ROOT / "checkpoints" / cid
        meta = json.loads((d / "checkpoint.json").read_text())
        assert meta["id"] == cid and meta["environment"] == c["environment"]
        files = {p.name for p in d.iterdir()}
        if c["environment"] == "appworld":
            assert files == {"checkpoint.json"}, cid
            assert not (ROOT / "conditions" / f"{cid}.json").exists()
        else:
            need = {"checkpoint.json", "history.json", "restore.json"} | ({"state.json.gz"} if c["environment"] != "bfcl" else set())
            assert need <= files, (cid, need - files)
            assert (ROOT / "conditions" / f"{cid}.json").exists(), cid


def test_condition_hashes():
    for f in (ROOT / "conditions").glob("*.json"):
        d = json.loads(f.read_text())
        assert d["conditions"]["U"] is None
        for c in ("N", "L", "PA"):
            x = d["conditions"][c]
            assert hashlib.sha256(x["text"].encode()).hexdigest() == x["sha256"], (f.name, c)
            assert x["text"].startswith("Note: an earlier action") or c == "PA"


def test_history_ends_at_the_cut():
    for cid, c in INDEX.items():
        if c["environment"] == "appworld":
            continue
        h = json.loads((ROOT / "checkpoints" / cid / "history.json").read_text())
        r = json.loads((ROOT / "checkpoints" / cid / "restore.json").read_text())
        if c["environment"] == "bfcl":
            assert len(h) == c["cut"] - 1, cid  # the history follows the harness's own system prompt
            assert len(r["replay"]) == r["replayed_calls"] and set(r["resume"]) == {"turn", "mid_turn", "steps_done_in_turn"}
        else:
            assert len(h) == r["history_messages"] == c["cut"], cid
        if c["environment"] != "bfcl":
            with gzip.open(ROOT / "checkpoints" / cid / "state.json.gz", "rt") as g:
                assert json.load(g)


def test_fixability_evidence():
    for cid, c in INDEX.items():
        if c["environment"] == "appworld":
            continue
        f = json.loads((ROOT / "checkpoints" / cid / "checkpoint.json").read_text())["fixability"]
        assert f["label"] == c["fixability"]
        if c["fixability"] == "proven_impossible":
            assert f["certificates"] and all(x["proof"] for x in f["certificates"])
        if c["fixability"] == "demonstrated" and c["split"] == "main":
            assert any(r["target"] == "correction" and r["executed_on_restored_checkpoint"] for r in f["demonstrated_routes"]), cid


def test_no_machine_specific_content():
    for p in list((ROOT / "checkpoints").rglob("*.json")) + list((ROOT / "conditions").glob("*.json")):
        t = p.read_text()
        for bad in ("/home/", "/nethome/", "/usr/", "127.0.0.1"):
            assert bad not in t, (p, bad)
