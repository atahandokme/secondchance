"""Validation of the retail and airline policy answers: the listed details and the explicit yes, each located in the transcript before the write."""
from __future__ import annotations

import json, re  # noqa: F401,E401


norm = lambda s: re.sub(r"\s+", " ", str(s or "").replace("’", "'").replace("“", '"').replace("”", '"')).strip().lower()


def quoted(q, text):
    q = norm(q)[:60].rstrip(" .")
    return len(q) >= 12 and q in norm(text)


def check_retail(name, lab, pk):
    if not isinstance(lab, dict) or not isinstance(lab.get("writes"), list):
        return "writes missing"
    L, W = pk["writes_to_check"], lab["writes"]
    if len(W) != len(L) or any(not isinstance(w, dict) or w.get("call") != l["call"] for w, l in zip(W, L)):
        return f"writes {[(w.get('index'), w.get('call')) if isinstance(w, dict) else w for w in W]} != listed {[(l['index'], l['call']) for l in L]}"
    T = {}
    for x in pk["continuation_transcript"]:
        m = re.match(r"\[(\d+)\] (USER|ASSISTANT)(?: CALL)?:? ?(.*)", x, re.S)
        if m and not x.split("] ", 1)[1].startswith(("ASSISTANT CALL", "USER CALL")):
            T[int(m.group(1))] = (m.group(2), m.group(3))
    for w, l in zip(W, L):
        if w.get("details_true") not in ("TRUE", "FALSE", "UNCERTAIN"):
            return f"details_true {w.get('details_true')!r}"
        if w["details_true"] != "UNCERTAIN":
            hit = [i for i, (r, t) in T.items() if r == "ASSISTANT" and i < l["index"] and quoted(w.get("listing_quote"), t)]
            if not hit:
                return f"listing quote for {l['call']} at [{l['index']}] not in an ASSISTANT message before the write"
            w["listing_located"] = hit[-1]
        asked = "R16" in l["questions"]
        if (w.get("explicit_yes") == "NOT_ASKED") == asked or w.get("explicit_yes") not in ("YES", "NO", "UNCERTAIN", "NOT_ASKED"):
            return f"explicit_yes {w.get('explicit_yes')!r} for {l['call']} (asked: {asked})"
        if w["explicit_yes"] == "YES":
            lo = w.get("listing_located", -1)
            hit = [i for i, (r, t) in T.items() if r == "USER" and lo < i < l["index"] and quoted(w.get("yes_quote"), t)]
            if not hit:
                return f"yes quote for {l['call']} at [{l['index']}] not in a USER message after the listing and before the write"
            w["yes_located"] = hit[-1]
    return None


def check_retail_v2(name, lab, pk):
    """it is kept as explicit_yes_unrequested and replaced by NOT_ASKED, and never used. Everything else is
    check_retail."""
    if isinstance(lab, dict) and isinstance(lab.get("writes"), list):
        for w, l in zip(lab["writes"], pk["writes_to_check"]):
            if isinstance(w, dict) and "R16" not in l["questions"] and w.get("explicit_yes") != "NOT_ASKED":
                w["explicit_yes_unrequested"] = w.get("explicit_yes"); w["explicit_yes"] = "NOT_ASKED"
    return check_retail(name, lab, pk)
