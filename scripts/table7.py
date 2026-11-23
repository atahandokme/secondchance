"""Table 7: Acceptance rule in decision order (see docs/scoring.md).
This table is descriptive (definitions, not results); its content is shipped in scripts/descriptive_tables.json.
  python scripts/table7.py"""
import json
from pathlib import Path

from common import show


def rows():
    return json.loads((Path(__file__).resolve().parent / "descriptive_tables.json").read_text())["7"]["rows"]


if __name__ == "__main__":
    show(rows())
