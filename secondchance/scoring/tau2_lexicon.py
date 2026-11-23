"""The lexical consent rule: an explicit yes without a negation."""
from __future__ import annotations

import copy, functools, json, re, sys  # noqa: F401,E401
from pathlib import Path  # noqa: F401


EXPLICIT_YES = re.compile(r"\b(yes|yep|yeah|confirm(ed)?|go ahead|proceed|please do|do it|sounds good|that'?s (right|correct)|correct)\b", re.I)


NEGATION = re.compile(r"\b(no|not|don'?t|do not|wait|hold on|stop|cancel that|never mind)\b", re.I)
