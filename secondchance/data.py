"""Access to the shipped checkpoints and assistance texts: a local copy of the repository (default: the folder that contains this package,
or SECONDCHANCE_HOME)."""
import gzip
import json
import os
from pathlib import Path


def home():
    h = os.environ.get("SECONDCHANCE_HOME")
    root = Path(h) if h else Path(__file__).resolve().parent.parent
    if not (root / "checkpoints" / "index.jsonl").exists():
        raise FileNotFoundError(f"no SecondChance data under {root}: clone the repository or set SECONDCHANCE_HOME")
    return root


def index():
    return {c["id"]: c for c in (json.loads(l) for l in (home() / "checkpoints" / "index.jsonl").read_text().splitlines() if l.strip())}


class Checkpoint:
    def __init__(self, cid):
        self.id = cid
        self.dir = home() / "checkpoints" / cid
        self.meta = json.loads((self.dir / "checkpoint.json").read_text())
        self.environment = self.meta["environment"]
        if self.environment == "appworld":
            raise ValueError(f"{cid}: AppWorld checkpoint contents are not distributed (AppWorld permits redistribution of its task data only in encrypted form)")
        self.history = json.loads((self.dir / "history.json").read_text())
        self.restore = json.loads((self.dir / "restore.json").read_text())
        self.task_id = self.meta["task_id"].split("/", 1)[1]
        c = home() / "conditions" / f"{cid}.json"
        self.conditions = json.loads(c.read_text())["conditions"] if c.exists() else {}

    def state(self):
        """the reference copy of the agent-side database at the checkpoint (tau2, retail, airline)"""
        with gzip.open(self.dir / "state.json.gz", "rt") as g:
            return json.load(g)

    def assistance(self, condition):
        """the frozen text appended to the agent's system prompt (None for U)"""
        x = self.conditions.get(condition)
        return None if x is None else x["text"]
