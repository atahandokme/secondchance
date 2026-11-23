"""Table 1: SecondChance and related benchmarks. Y full support, P partial support, N no support.
This table is descriptive (definitions, not results); its content is shipped in scripts/descriptive_tables.json.
  python scripts/table1.py"""
import json
from pathlib import Path

from common import show


def rows():
    return json.loads((Path(__file__).resolve().parent / "descriptive_tables.json").read_text())["1"]["rows"]


if __name__ == "__main__":
    show(rows())
