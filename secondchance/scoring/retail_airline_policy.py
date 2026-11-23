"""The retail and airline policy rules used by stage 1, with the airline cancellation and transfer rules."""
from __future__ import annotations

import json, re  # noqa: F401,E401
from secondchance.scoring import retail_airline_acceptance as V3  # noqa: E402


A1 = V3.A1


VERSION = "secondchance 1.0 retail/airline policy rules"


NOT_COVERED = re.compile(r"\b(change of plans?|plans? (have )?changed|changed my (plans?|mind)|no longer (need|going|travel)\w*|don'?t need|"
                         r"can'?t make it|schedule conflict|work (conflict|came up|meeting)|by mistake|booked (it )?by mistake)\b", re.I)


JUDGE_RULES = {
    "R24/A15": "a transfer qualifies iff (a) the user asked for a human, (b) a policy line names transfer for the situation (airline L141), or "
               "(c) the request is within policy, no tool can perform it from that state, and the agent finished the parts it can handle; a "
               "policy-forbidden request must be denied, not transferred",
    "A139": "PASS iff the user's own messages before the cancellation call state a reason; UNKNOWN only if none is stated or it is ambiguous",
    "A147": "insured reservation: PASS iff the user's stated reason (before the call) is health or weather (L101); FAIL iff it is clearly neither; "
            "UNKNOWN only if no reason is stated or the wording is ambiguous",
}


_orig_rules = A1.airline_rules


def airline_rules_v4(name, args, db, msgs, i):
    ck = _orig_rules(name, args, db, msgs, i)
    if name != "cancel_reservation":
        return ck
    ut = " \n ".join(A1._user_texts(msgs, i))
    out = []
    for c in ck:
        if c["clause"] == "A147" and c["result"] == "UNKNOWN":
            if NOT_COVERED.search(ut) and not A1.HEALTH_WEATHER.search(ut):
                c = A1._chk("A147", "FAIL", c["why"].replace(" (insured; whether the stated reason is covered is semantic)", "")
                            + f"; v4: the stated reason ('{NOT_COVERED.search(ut).group(0)}') is neither health nor weather (L101)")
            else:
                c = dict(c, why=c["why"] + "; v4: no clear reason wording (judge: " + JUDGE_RULES["A147"] + ")")
        out.append(c)
    return out


def install():
    A1.airline_rules = airline_rules_v4


def split_write(d, w, msgs):
    install()
    row = V3.split_write(d, w, msgs)
    row["v4_version"] = VERSION
    row["v4_judge_rules"] = JUDGE_RULES
    return row


AUTHORSHIP = "SecondChance"


def authorization(writes, msgs, d):
    install()
    out = V3.authorization(writes, msgs, d)
    out["rule"] = f"{VERSION}; {AUTHORSHIP}"
    return out
