"""Table 9: Continuation budgets: each environment's own limit (retail and airline use the tau2 limit).
This table is descriptive (definitions, not results); its content is shipped in scripts/descriptive_tables.json.
  python scripts/table9.py"""
import json
from pathlib import Path

from common import show


def rows():
    return json.loads((Path(__file__).resolve().parent / "descriptive_tables.json").read_text())["9"]["rows"]


if __name__ == "__main__":
    show(rows())
