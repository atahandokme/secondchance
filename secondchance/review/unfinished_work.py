"""The unfinished-work question: the agent's last message to the user, validation of the extracted steps, and the label derived from them (a step still outstanding at the end, or the request said to be unresolved)."""
from __future__ import annotations

import json, re  # noqa: F401,E401


def derive(lab):
    """the label from the extracted facts (rule q4, 'outstanding at the end'):
    YES      a step of the agent's last message is outstanding (unconditional, or its condition came true, and not carried out), or the
             last message plainly says the request is unresolved; UNKNOWN  no such step, but a not-carried-out step has an UNKNOWN condition; NO       otherwise (every applicable step was carried out, no step was asked, no last message, or the message claims it is resolved)."""
    steps = lab.get("steps") or []
    live = [s for s in steps if s.get("carried_out") == "NO" and (s.get("condition") in (None, "", "NONE") or s.get("condition_met") in ("YES", "NA"))]
    unk = [s for s in steps if s.get("carried_out") == "NO" and s.get("condition") not in (None, "", "NONE") and s.get("condition_met") == "UNKNOWN"]
    if live or lab.get("says_unresolved") == "YES":
        return "YES"
    return "UNKNOWN" if unk else "NO"


def last_agent(T):
    """the agent's last message to the user: the last ASSISTANT text entry with at least 15 characters once thought markers are removed."""
    best = None
    for t in T:
        m = re.match(r"\[(\d+)\] ASSISTANT: (.*)", t, re.S)
        if m and len(re.sub(r"<\|?channel\|?>|thought", "", m.group(2)).strip()) >= 15:
            best = int(m.group(1))
    return best


def check(lab, T):
    idx = {int(m.group(1)): t for t in T for m in [re.match(r"\[(\d+)\] ", t)] if m}
    la = last_agent(T)
    if lab.get("last_agent_message_index") != la:
        return f"last_agent_message_index must be {la}"
    order = [int(re.match(r"\[(\d+)\] ", t).group(1)) for t in T]
    kind = [t for t in T]
    for s in lab.get("steps") or []:
        if s.get("carried_out") not in ("YES", "NO") or s.get("condition_met") not in ("YES", "NO", "UNKNOWN", "NA"):
            return f"bad step fields {s}"
        b = s.get("by_entry")
        if s["carried_out"] == "YES":
            # a USER entry numbered b after the message, or the TOOL RESULT directly after a USER CALL (then the call is what carried it out)
            pos = [k for k, n in enumerate(order) if n == b]
            ok = any(re.match(r"\[\d+\] USER", kind[k]) or (re.match(r"\[\d+\] TOOL RESULT", kind[k]) and k > 0 and re.match(r"\[\d+\] USER CALL", kind[k - 1])) for k in pos)
            if b is None or la is None or b <= la or not ok:
                return f"carried_out YES without a USER entry after the message ({b})"
    if lab.get("says_unresolved") not in ("YES", "NO"):
        return "bad says_unresolved"
    if lab.get("says_unresolved") == "YES" and len(str(lab.get("unresolved_quote") or "")) < 8:
        return "says_unresolved YES without a quote"
    lab["unfinished_work_acknowledged"] = derive(lab)
    return None
