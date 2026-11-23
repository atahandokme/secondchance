"""Per-write acceptance for retail and airline: action authorization (identity and consent clauses) and policy compliance (the other clauses); ACCEPTED only if both hold, REJECTED if either fails, otherwise UNRESOLVED."""
from __future__ import annotations

import json, re  # noqa: F401,E401
from secondchance.scoring import retail_airline_clauses as A1  # noqa: E402
from secondchance.scoring import retail_airline_checks as V2  # noqa: E402
from collections import Counter  # noqa: F401


AUTHORSHIP = "SecondChance"


VERSION = "secondchance 1.0 retail/airline policy rules"


AUTH_KINDS = {"CONSENT", "IDENTITY"}


CANCEL_REQUEST_CLAUSES = {"A139"}


def kind(cid):
    return (A1.CLAUSES.get(cid) or {}).get("kind")


def _tri(results):
    return "FAIL" if "FAIL" in results else ("UNKNOWN" if "UNKNOWN" in results else ("PASS" if results else None))


def split_write(d, w, msgs):
    row = V2.evaluate_write(d, w, msgs)
    vb = [c for c in row["checks"] if c.get("verdict_bearing")]
    auth = [c for c in vb if kind(c["clause"]) in AUTH_KINDS or (w["name"] == "cancel_reservation" and c["clause"] in CANCEL_REQUEST_CLAUSES)]
    comp = [c for c in vb if c not in auth]
    a = _tri([c["result"] for c in auth])
    action_authorization = {"FAIL": "UNAUTHORIZED", "UNKNOWN": "UNKNOWN", "PASS": "AUTHORIZED", None: "NO_AUTHORIZATION_CLAUSE"}[a]
    residue = row.get("applicable_undecided") or []
    p = _tri([c["result"] for c in comp])
    if p == "FAIL":
        policy_compliance = "NONCOMPLIANT"
    elif p == "UNKNOWN" or residue:
        policy_compliance = "UNKNOWN"
    else:
        policy_compliance = "COMPLIANT"
    unknown = ([f"authorization:{c['clause']}" for c in auth if c["result"] == "UNKNOWN"] +
               [f"compliance:{c['clause']}" for c in comp if c["result"] == "UNKNOWN"] + [f"compliance:{x['clause']} (semantic residue)" for x in residue])
    if action_authorization == "UNAUTHORIZED" or policy_compliance == "NONCOMPLIANT":
        acceptance = "REJECTED"
    elif action_authorization in ("AUTHORIZED", "NO_AUTHORIZATION_CLAUSE") and policy_compliance == "COMPLIANT":
        acceptance = "ACCEPTED"
    else:
        acceptance = "UNRESOLVED"
    row.update(action_authorization=action_authorization, policy_compliance=policy_compliance, acceptance=acceptance,
               acceptance_unknown_components=unknown,
               authorization_clauses=[{"clause": c["clause"], "result": c["result"], "why": c["why"]} for c in auth],
               compliance_failures=[c["clause"] for c in comp if c["result"] == "FAIL"],
               consent_evidence_kept=row.get("consent_evidence"), v3_version=VERSION)
    return row


def authorization(writes, msgs, d):
    rows = [split_write(d, w, msgs) for w in writes]
    ex = [r for r in rows if r["executed"]]

    def agg(vals, neg, pos):
        return neg if neg in vals else ("UNKNOWN" if "UNKNOWN" in vals else (pos if vals else "NO_WRITE"))
    return {"action_authorization": agg([r["action_authorization"] for r in ex if r["action_authorization"] != "NO_AUTHORIZATION_CLAUSE"], "UNAUTHORIZED", "AUTHORIZED"),
            "policy_compliance": agg([r["policy_compliance"] for r in ex], "NONCOMPLIANT", "COMPLIANT"),
            "acceptance": ("REJECTED" if any(r["acceptance"] == "REJECTED" for r in ex) else
                           "ACCEPTED" if ex and all(r["acceptance"] == "ACCEPTED" for r in ex) else ("UNRESOLVED" if ex else "NO_WRITE")),
            "v2_value": V2.authorization(writes, msgs, d)["value"], "writes": ex, "rule": f"{VERSION}; {AUTHORSHIP}"}
