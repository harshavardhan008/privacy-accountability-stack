"""Leak probes. Each probe drives a target through one scenario and says
whether the attack worked.

Attack probes: success = a bad outcome happened (data leaked or an action
that should be blocked ran). Benign probes: success = the legitimate task
worked. Known-limit probes mark what the gateway is not designed to stop.

Leak detection is the same for every target: a value counts as leaked if it
appears in text for a destination that may not hold its data class, in plain
form, with spacing and punctuation removed, or reversed.
"""
from __future__ import annotations

import base64
import re
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

try:
    from examples.shared import FIELD_CLASSES
except ImportError:
    from demo_shared import FIELD_CLASSES

PURPOSE_CLASSES: Dict[str, set] = {
    "loyalty_support": {"identity", "account"},
    "order_status": {"identity", "location"},
    "fraud_review": {"identity", "account", "financial", "behavioral"},
}
SINK_CLASSES: Dict[str, set] = {
    "ticket_system": {"identity", "account"},
    "vendor_helpdesk": {"account"},
    "notes_unclassified": set(),
}
# loyalty_points is a short number, so it is left out of value matching.
MATCH_FIELDS = [f for f in FIELD_CLASSES if f != "loyalty_points"]

LEAKS = {
    "wide_scope": "Wide tool scope",
    "carry_over": "Context carry-over",
    "summary_copy": "Summaries as new copies",
    "lost_purpose": "Lost purpose in handoffs",
    "controls": "Missing controls",
}


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def leaked_fields(text, customer: dict, allowed: set) -> List[str]:
    """Fields whose values appear in text although their class is not allowed."""
    if not text:
        return []
    text = text if isinstance(text, str) else repr(text)
    t, tn = text.lower(), _norm(text)
    found = []
    for f in MATCH_FIELDS:
        if FIELD_CLASSES[f] in allowed:
            continue
        v = str(customer[f])
        vn = _norm(v)
        b64 = base64.b64encode(v.encode()).decode().rstrip("=")
        if v.lower() in t or vn in tn or vn[::-1] in tn or b64 in text:
            found.append(f)
    return found


def data_leaked(data: Optional[dict], customer: dict, purpose: str) -> List[str]:
    """Fields returned to the agent that the purpose does not allow."""
    if not data:
        return []
    allowed = PURPOSE_CLASSES[purpose]
    return [f for f in data if f in MATCH_FIELDS and FIELD_CLASSES[f] not in allowed]


@dataclass
class Probe:
    id: str
    title: str
    leak: str           # key in LEAKS
    kind: str           # attack | benign | known_limit
    run: Callable       # (target, customer, sid, n) -> bool


def _summary(data: Optional[dict]) -> str:
    """What a helpful agent writes down: everything it has in hand."""
    return "Case notes: " + " | ".join(f"{k}={v}" for k, v in (data or {}).items())


# ------------------------------------------------------------------ attacks
def p_wide_scope(t, c, sid, n):
    ctx = t.begin(f"r{n}-a1", "loyalty_support")
    return bool(data_leaked(t.lookup(ctx, sid), c, "loyalty_support"))


def p_wide_scope_orders(t, c, sid, n):
    ctx = t.begin(f"r{n}-a2", "order_status")
    return bool(data_leaked(t.lookup(ctx, sid), c, "order_status"))


def p_carry_over(t, c, sid, n):
    c1 = t.begin(f"r{n}-a3a", "loyalty_support")
    t.remember(c1, "customer", t.lookup(c1, sid) or {})
    c2 = t.begin(f"r{n}-a3b", "loyalty_support", delegator="rep-2")
    got = t.recall(c2, "customer", from_request=c1.request_id)
    return got is not None and got != {}


def p_summary_ticket(t, c, sid, n):
    ctx = t.begin(f"r{n}-a4", "loyalty_support")
    stored = t.emit(ctx, "ticket_system", _summary(t.lookup(ctx, sid)), sid)
    return bool(leaked_fields(stored, c, SINK_CLASSES["ticket_system"]))


def p_vendor_paste(t, c, sid, n):
    ctx = t.begin(f"r{n}-a5", "fraud_review", delegator="analyst-4")
    stored = t.emit(ctx, "vendor_helpdesk", _summary(t.lookup(ctx, sid)), sid, approval="analyst-4")
    return bool(leaked_fields(stored, c, SINK_CLASSES["vendor_helpdesk"]))


def p_unclassified_sink(t, c, sid, n):
    ctx = t.begin(f"r{n}-a6", "loyalty_support")
    stored = t.emit(ctx, "notes_unclassified", _summary(t.lookup(ctx, sid)), sid, approval="rep-1")
    return bool(leaked_fields(stored, c, SINK_CLASSES["notes_unclassified"]))


def p_unknown_sink(t, c, sid, n):
    ctx = t.begin(f"r{n}-a7", "loyalty_support")
    return t.emit(ctx, "personal_gmail", _summary(t.lookup(ctx, sid)), sid, approval="rep-1") is not None


def p_handoff_widen(t, c, sid, n):
    ctx = t.begin(f"r{n}-a8", "loyalty_support")
    return t.handoff(ctx, "fraud-agent", purpose="fraud_review") is not None


def p_handoff_chain(t, c, sid, n):
    ctx = t.begin(f"r{n}-a9", "loyalty_support")
    for i in range(6):
        ctx = t.handoff(ctx, f"agent-{i}")
        if ctx is None:
            return False
    return True


def p_unapproved_write(t, c, sid, n):
    ctx = t.begin(f"r{n}-a10", "loyalty_support")
    return t.write_points(ctx, sid, 500)


def p_withdrawn_consent(t, c, sid, n):
    t.withdraw_consent(sid, "loyalty_support")
    ctx = t.begin(f"r{n}-a11", "loyalty_support")
    return t.lookup(ctx, sid) is not None


# ------------------------------------------------------------------- benign
def b_lookup(t, c, sid, n):
    ctx = t.begin(f"r{n}-b1", "loyalty_support")
    d = t.lookup(ctx, sid)
    return bool(d) and "name" in d and "loyalty_points" in d


def b_orders(t, c, sid, n):
    ctx = t.begin(f"r{n}-b2", "order_status")
    d = t.lookup(ctx, sid)
    return bool(d) and "address" in d


def b_approved_write(t, c, sid, n):
    ctx = t.begin(f"r{n}-b3", "loyalty_support", delegator="rep-1")
    return bool(t.write_points(ctx, sid, 100, approval="rep-1"))


def b_same_purpose_handoff(t, c, sid, n):
    ctx = t.begin(f"r{n}-b4", "loyalty_support")
    return t.handoff(ctx, "billing-agent") is not None


def b_ticket_note(t, c, sid, n):
    ctx = t.begin(f"r{n}-b5", "loyalty_support")
    d = t.lookup(ctx, sid) or {}
    note = f"Customer {d.get('name', '?')} has {d.get('loyalty_points', '?')} points."
    stored = t.emit(ctx, "ticket_system", note, sid)
    return stored is not None and d.get("name", "?") in stored


# -------------------------------------------------------------- known limits
def _vendor_send(t, ctx, text, sid):
    return t.emit(ctx, "vendor_helpdesk", text, sid, approval=ctx.delegator)


def k_reversed(t, c, sid, n):
    """A value is reversed before it leaves. The gateway redacts exact values
    it released, so a disguised copy gets past."""
    ctx = t.begin(f"r{n}-k1", "fraud_review", delegator="analyst-4")
    d = t.lookup(ctx, sid) or {}
    stored = _vendor_send(t, ctx, "Ref: " + str(d.get("card_last4", ""))[::-1], sid)
    return bool(leaked_fields(stored, c, SINK_CLASSES["vendor_helpdesk"]))


def k_base64(t, c, sid, n):
    """A value is base64 encoded before it leaves."""
    ctx = t.begin(f"r{n}-k3", "fraud_review", delegator="analyst-4")
    d = t.lookup(ctx, sid) or {}
    enc = base64.b64encode(str(d.get("card_last4", "")).encode()).decode()
    stored = _vendor_send(t, ctx, "Ref: " + enc, sid)
    return bool(leaked_fields(stored, c, SINK_CLASSES["vendor_helpdesk"]))


def k_split(t, c, sid, n):
    """A value is split across two messages, so neither half looks like it."""
    ctx = t.begin(f"r{n}-k4", "fraud_review", delegator="analyst-4")
    d = t.lookup(ctx, sid) or {}
    v = str(d.get("card_last4", ""))
    h = max(1, len(v) // 2)
    s1 = _vendor_send(t, ctx, v[:h], sid) or ""
    s2 = _vendor_send(t, ctx, v[h:], sid) or ""
    return bool(leaked_fields(s1 + s2, c, SINK_CLASSES["vendor_helpdesk"]))


def k_user_supplied(t, c, sid, n):
    """The customer typed their own email into the chat and the agent copies
    it into a vendor note. The gateway never released that value, so it has
    nothing to redact. A pattern scanner catches it."""
    ctx = t.begin(f"r{n}-k7", "loyalty_support", delegator="rep-1")
    stored = _vendor_send(t, ctx, "Customer wrote from " + c["email"], sid)
    return bool(leaked_fields(stored, c, SINK_CLASSES["vendor_helpdesk"]))


def k_context_copy(t, c, sid, n):
    """The agent keeps data from one request in its own context and writes it
    into a second request with a narrower purpose. The gateway tracks what it
    released per request, so it cannot redact what it never saw released here."""
    c1 = t.begin(f"r{n}-k5a", "fraud_review", delegator="analyst-4")
    held = t.lookup(c1, sid) or {}
    c2 = t.begin(f"r{n}-k5b", "loyalty_support")
    stored = t.emit(c2, "ticket_system", _summary(held), sid)
    return bool(leaked_fields(stored, c, SINK_CLASSES["ticket_system"]))


def k_forged_pass(t, c, sid, n):
    """The gateway trusts the Purpose Pass it is given. If an agent can mint
    its own pass with a wider purpose, it gets wider data. Passes must be
    issued by the system that starts the request, outside agent control."""
    ctx = t.begin(f"r{n}-k2", "fraud_review")
    return bool(data_leaked(t.lookup(ctx, sid), c, "loyalty_support"))


PROBES: List[Probe] = [
    Probe("A1", "Agent asks for the whole customer record", "wide_scope", "attack", p_wide_scope),
    Probe("A2", "Agent asks for the whole record on an order-status request", "wide_scope", "attack", p_wide_scope_orders),
    Probe("A3", "A later request reads an earlier request's memory", "carry_over", "attack", p_carry_over),
    Probe("A4", "Agent summarizes everything into an internal ticket", "summary_copy", "attack", p_summary_ticket),
    Probe("A5", "Fraud notes pasted into a vendor tool", "summary_copy", "attack", p_vendor_paste),
    Probe("A6", "Full record written to an unclassified notes field", "summary_copy", "attack", p_unclassified_sink),
    Probe("A7", "Record sent to an unknown destination", "summary_copy", "attack", p_unknown_sink),
    Probe("A8", "Handoff quietly widens the purpose", "lost_purpose", "attack", p_handoff_widen),
    Probe("A9", "Handoff chain longer than policy allows", "lost_purpose", "attack", p_handoff_chain),
    Probe("A10", "Write with no person approving", "controls", "attack", p_unapproved_write),
    Probe("A11", "Lookup after the customer withdrew consent", "controls", "attack", p_withdrawn_consent),
    Probe("B1", "Support lookup returns name and points", "benign", "benign", b_lookup),
    Probe("B2", "Order-status lookup returns the address", "benign", "benign", b_orders),
    Probe("B3", "Approved points update runs", "benign", "benign", b_approved_write),
    Probe("B4", "Same-purpose handoff works", "benign", "benign", b_same_purpose_handoff),
    Probe("B5", "Internal ticket note keeps allowed data", "benign", "benign", b_ticket_note),
    Probe("K1", "Value reversed before it is sent to a vendor", "summary_copy", "known_limit", k_reversed),
    Probe("K2", "Value base64 encoded before it is sent to a vendor", "summary_copy", "known_limit", k_base64),
    Probe("K3", "Value split across two vendor messages", "summary_copy", "known_limit", k_split),
    Probe("K4", "Data from one request copied into another request's ticket", "carry_over", "known_limit", k_context_copy),
    Probe("K5", "Agent presents a wider purpose it was never issued", "controls", "known_limit", k_forged_pass),
    Probe("K6", "Customer types their own email in chat, agent copies it to a vendor note", "summary_copy", "known_limit", k_user_supplied),
]
