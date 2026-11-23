"""Check every table and Figure 2 of the paper against the numbers printed in the submitted version.

tests/expected/paper_tables.json holds each table of the submitted paper as printed (cells with LaTeX formatting removed) and the
Figure 2 grid. For the data tables, every row after the column headings that contains a digit must equal the corresponding row printed by
the table script, in order; the descriptive tables (1, 2, 6, 7, 8, 9) must be equal row for row.
  python scripts/verify.py                                   checks the files shipped in this repository
  SECONDCHANCE_DATA=hf:<dataset> python scripts/verify.py    checks the rows of the Hugging Face dataset"""
import importlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
EXPECTED = json.loads((HERE.parent / "tests" / "expected" / "paper_tables.json").read_text())
LABEL = {1: "tab:comparison", 2: "tab:assistance-conditions", 3: "tab:main", 4: "tab:appendix-selection", 5: "tab:appendix-kinds",
         6: "tab:checkpoint-annotations", 7: "tab:appendix-decision", 8: "tab:appendix-models", 9: "tab:appendix-budgets", 10: "tab:appendix-studies",
         11: "tab:scorecard", 12: "tab:appendix-full-grid", 13: "tab:main-outcomes", 14: "tab:appendix-assistance-paired",
         15: "tab:appendix-acceptance-standards", 16: "tab:appendix-strict", 17: "tab:appendix-work", 18: "tab:appendix-durability", 19: "tab:appendix-controls"}
HEADER_ROWS = {3: 2, 4: 1, 5: 2, 10: 1, 11: 3, 12: 2, 13: 2, 14: 2, 15: 1, 16: 2, 17: 2, 18: 2, 19: 1}
DESCRIPTIVE = (1, 2, 6, 7, 8, 9)


def has_digit(row):
    return any(ch.isdigit() for ch in "".join(row))


def check_table(n):
    """(ok, number of rows compared, first difference or None)"""
    got = importlib.import_module(f"table{n}").rows()
    paper = EXPECTED["tables"][LABEL[n]]["rows"]
    if n in DESCRIPTIVE:
        want = paper
    else:
        want = [r for r in paper[HEADER_ROWS[n]:] if has_digit(r)]
        got = [r for r in got if has_digit(r)]
    for i, (a, b) in enumerate(zip(got, want)):
        if a != b:
            return False, len(want), {"row": i, "script": a, "paper": b}
    if len(got) != len(want):
        return False, len(want), {"rows_script": len(got), "rows_paper": len(want)}
    return True, len(want), None


def check_figure2():
    import figure2
    got, want = figure2.grid(), EXPECTED["figure2"]
    if got != want:
        return False, sum(len(v) for v in want.values()), {k: [a, b] for k in want for a, b in zip(got.get(k, []), want[k]) if a != b}
    return True, sum(len(v) for v in want.values()), None


def numbers_in(rows):
    import re
    # numeric cells only: the first cell of a row is its label (model names such as Qwen3-235B are not counted)
    return sum(len(re.findall(r"(?<![A-Za-z\d.])[-+]?(?:\d[\d,]*)?\.?\d+", " ".join(r[1:]))) for r in rows)


def main():
    bad = 0
    total_numbers = 0
    for n in range(1, 20):
        ok, k, diff = check_table(n)
        if n not in DESCRIPTIVE:
            total_numbers += numbers_in([r for r in EXPECTED["tables"][LABEL[n]]["rows"][HEADER_ROWS[n]:] if has_digit(r)])
        print(f"Table {n:2d}  {'OK  ' if ok else 'DIFF'}  {k} rows" + ("" if ok else f"  {json.dumps(diff)}"))
        bad += not ok
    ok, k, diff = check_figure2()
    print(f"Figure 2  {'OK  ' if ok else 'DIFF'}  {k} model rows x 3 panels" + ("" if ok else f"  {json.dumps(diff)}"))
    bad += not ok
    print(("ALL MATCH" if not bad else f"{bad} ARTIFACT(S) DIFFER") + f": {total_numbers} printed numbers in the data tables, plus 684 Figure 2 cells")
    return bad


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
