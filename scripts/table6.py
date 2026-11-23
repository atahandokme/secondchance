"""Table 6: Evaluator-only annotations. The agent sees only the history and what its condition supplies.
This table is descriptive (definitions, not results); its content is shipped in scripts/descriptive_tables.json.
  python scripts/table6.py"""
import json
from pathlib import Path

from common import show


def rows():
    return json.loads((Path(__file__).resolve().parent / "descriptive_tables.json").read_text())["6"]["rows"]


if __name__ == "__main__":
    show(rows())
