"""Parsing of a judge reply: the JSON object it contains."""
from __future__ import annotations

import json, re  # noqa: F401,E401


def parse(txt):
    txt = re.sub(r"^```(?:json)?\s*|\s*```\s*$", "", txt.strip())
    i, j = txt.find("{"), txt.rfind("}")
    return json.loads(txt[i:j + 1])
