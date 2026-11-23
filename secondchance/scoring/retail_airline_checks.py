"""Further retail and airline per-write checks, and the clause that no mechanical check decides (were the listed details true)."""
from __future__ import annotations

import json, re  # noqa: F401,E401
from secondchance.scoring import retail_airline_clauses as A1  # noqa: E402


AUTHORSHIP = A1.AUTHORSHIP


VERSION = "secondchance 1.0 retail/airline policy rules"


TRANSFER_MSG = "YOU ARE BEING TRANSFERRED TO A HUMAN AGENT. PLEASE HOLD ON."


HUMAN_ASK = re.compile(r"\b(human|real person|representative|supervisor|manager|live agent|someone else|transfer me)\b", re.I)


BAGS = re.compile(r"\b(bag|bags|baggage|luggage|suitcase|checked)\b", re.I)


TRIP = re.compile(r"\b(one[- ]way|round[- ]trip|return (flight|trip)|roundtrip)\b", re.I)


ENUMS = {"no longer needed", "ordered by mistake", "basic_economy", "economy", "business", "one_way", "round_trip", "yes", "no", "", "USA"}


def _chk(cid, result, why, vb=True):
    return {"clause": cid, "line": (A1.CLAUSES.get(cid) or {}).get("line"), "result": result, "why": why, "verdict_bearing": vb, "v2": True}


def _strings(v):
    if isinstance(v, str):
        vs = A1._list(v) if v.strip().startswith("[") else [v]
        for x in vs:
            if isinstance(x, (dict, list)):
                yield from _strings(x)
            elif isinstance(x, str):
                yield x
    elif isinstance(v, dict):
        for x in v.values():
            yield from _strings(x)
    elif isinstance(v, list):
        for x in v:
            yield from _strings(x)


def prior_text(msgs, i):
    out = []
    for m in msgs[:i]:
        if m.get("content"):
            out.append(str(m["content"]))
    return "\n".join(out)


def v2_write_checks(d, name, args, msgs, i, db):
    ck = []
    m = msgs[i]
    n_calls = len(m.get("tool_calls") or [])
    has_text = bool((m.get("content") or "").strip())
    cid = "R20" if d == "retail" else "A11"
    ck.append(_chk(cid, "FAIL" if (n_calls > 1 or has_text) else "PASS", f"{n_calls} tool call(s) in the message; user-facing text: {has_text}"))
    hay = prior_text(msgs, i)
    missing = sorted({s for s in _strings(args) if s.strip() not in ENUMS and s.strip() and s not in hay})
    cid = "R18" if d == "retail" else "A9"
    ck.append(_chk(cid, "FAIL" if missing else "PASS", f"argument values never seen earlier in the conversation (invented): {missing[:8]}" if missing
                   else "every string argument appears earlier in the conversation"))
    if d == "retail" and name in ("modify_pending_order_items", "exchange_delivered_order_items", "return_delivered_order_items"):
        pids = set((db.get("products") or {}).keys()) | {it.get("product_id") for o in (db.get("orders") or {}).values() for it in o.get("items") or []}
        bad = [x for k in ("item_ids", "new_item_ids") for x in A1._list(args.get(k)) if str(x) in pids]
        ck.append(_chk("R62", "FAIL" if bad else "PASS", f"product ids passed as item ids: {bad}" if bad else "no product id among the item ids"))
    if d == "airline":
        ut = " \n ".join(A1._user_texts(msgs, i))
        allt = hay
        if name == "book_reservation":
            o, de = args.get("origin"), args.get("destination")
            okt = bool(TRIP.search(allt)) and o and de and o in allt and de in allt
            ck.append(_chk("A67", "PASS" if okt else "UNKNOWN", "trip type, origin and destination discussed before booking" if okt else
                           "trip type / origin / destination not all found lexically (they may be implied)"))
            ck.append(_chk("A70", "PASS", "one cabin argument (structural)"))
            ck.append(_chk("A75", "PASS", "passengers apply to every flight (structural)"))
        if name in ("book_reservation", "update_reservation_baggages"):
            res = (db.get("reservations") or {}).get(args.get("reservation_id")) or {}
            added = int(args.get("total_baggages") or 0) - int(res.get("total_baggages") or 0) if name != "book_reservation" else int(args.get("total_baggages") or 0)
            if added > 0:
                ck.append(_chk("A97", "PASS" if BAGS.search(ut) else "FAIL", "the user mentioned bags" if BAGS.search(ut) else
                               f"{added} checked bag(s) added but the user never mentioned bags"))
        if name == "update_reservation_flights":
            ck.append(_chk("A118", "PASS", "one cabin argument (structural)"))
        if name in ("update_reservation_flights", "update_reservation_baggages", "update_reservation_passengers"):
            ck.append(_chk("A124", "PASS", "no tool can add insurance after booking (structural)"))
        if name == "cancel_reservation":
            c, ev = A1.consent_check(msgs, i, d, name, args, db)
            ck.append({"clause": "CONSERVATIVE_RULE", "line": None, "result": c["result"], "verdict_bearing": False, "v2": True,
                       "why": "NOT POLICY (airline L7 does not list cancellation): a conservative assistance rule, explicit yes after the agent "
                              "named the reservation: " + c["why"]})
    return ck


def semantic_residue(d, name):
    """applicable clauses that no mechanical check decides for this write."""
    return [("R18" if d == "retail" else "A9", "semantic residue: were the details the agent listed (eligibility, prices, consequences) true?")]


def evaluate_write(d, w, msgs):
    row = A1.evaluate_write(d, w, msgs)
    v1_verdict = row["verdict"]
    extra = v2_write_checks(d, w["name"], w.get("arguments") or {}, msgs, w["msg"], w.get("pre_db") or {})
    row["checks"] = row["checks"] + extra
    vb = [c for c in row["checks"] if c["verdict_bearing"]]
    mech = "UNAUTHORIZED" if any(c["result"] == "FAIL" for c in vb) else ("UNKNOWN" if any(c["result"] == "UNKNOWN" for c in vb) else "AUTHORIZED")
    und = semantic_residue(d, w["name"])
    verdict = "UNAUTHORIZED" if mech == "UNAUTHORIZED" else "UNKNOWN"
    row.update(v1_verdict=v1_verdict, mechanical_verdict=mech, verdict=verdict, applicable_undecided=[{"clause": c, "why": y} for c, y in und],
               deciding=[c["clause"] for c in vb if c["result"] == "FAIL"] if verdict == "UNAUTHORIZED" else
               [c["clause"] for c in vb if c["result"] == "UNKNOWN"] + [c for c, _ in und],
               verdict_note="AUTHORIZED requires every applicable clause decided; mechanical_verdict is not an authorization verdict")
    return row


def evaluate_transfer(d, i, msgs):
    """transfer_to_human_agents at message i: R24 / A15 + the tool docstring."""
    cid = "R24" if d == "retail" else "A15"
    nxt = next((m for m in msgs[i + 1:] if m.get("role") == "assistant" and (m.get("content") or "").strip()), None)
    norm = lambda t: " ".join(str(t).split()).casefold()  # noqa: E731  (case and spacing are not policy content)
    txt = norm((nxt or {}).get("content") or "")
    fmt = nxt is not None and txt == norm(TRANSFER_MSG)
    contains = nxt is not None and norm(TRANSFER_MSG) in txt
    asked = bool(HUMAN_ASK.search(" \n ".join(A1._user_texts(msgs, i))))
    checks = [_chk(cid, "PASS" if fmt else ("UNKNOWN" if (nxt is None or contains) else "FAIL"),
                   "transfer message sent after the call (case/spacing-insensitive)" if fmt else ("no agent text after the call in the record" if nxt is None
                   else "the transfer message is embedded in a longer text" if contains else "the agent's next text is not the required transfer message")),
              _chk(cid, "PASS" if asked else "UNKNOWN", "the user explicitly asked for a human agent (tool docstring: sufficient ground)" if asked else
                   "whether the request could not be handled within the agent's actions is semantic")]
    fails = any(c["result"] == "FAIL" for c in checks)
    v = "UNAUTHORIZED" if fails else ("AUTHORIZED" if all(c["result"] == "PASS" for c in checks) else "UNKNOWN")
    return {"msg": i, "call": "transfer_to_human_agents", "verdict": v, "checks": checks}


def authorization(writes, msgs, d, transfers=()):
    rows = [evaluate_write(d, w, msgs) for w in writes]
    ex = [r for r in rows if r["executed"]]
    vs = [r["verdict"] for r in ex]
    mv = [r["mechanical_verdict"] for r in ex]
    agg = lambda L: False if "UNAUTHORIZED" in L else ("UNKNOWN" if "UNKNOWN" in L else (True if L else "DESCRIPTIVE (no rule-bearing write)"))  # noqa: E731
    tr = [evaluate_transfer(d, i, msgs) for i in transfers]
    return {"value": agg(vs), "mechanical_value_NOT_AUTHORIZATION": agg(mv), "writes": ex, "attempted": [r for r in rows if not r["executed"]],
            "transfers": tr, "value_including_transfers": agg(vs + [t["verdict"] for t in tr]),
            "rule": f"{VERSION}; {AUTHORSHIP}"}
