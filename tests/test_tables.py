"""Every table and Figure 2 of the paper, recomputed from the shipped results, equals the submitted version (OpenReview submission 153).
Set SECONDCHANCE_DATA=hf:<dataset> to run the same checks on the rows of the Hugging Face dataset."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import verify  # noqa: E402


@pytest.mark.parametrize("n", range(1, 20))
def test_table(n):
    ok, rows, diff = verify.check_table(n)
    assert ok, diff


def test_figure2():
    ok, rows, diff = verify.check_figure2()
    assert ok, diff
