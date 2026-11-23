"""Two agents with the same tools: one calls them directly, one goes through
the purpose gateway. Probes drive both through the same interface."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from aar import PolicyDenied, PurposePass, subject_ref
try:  # repo layout: agent-action-record/ is on the path
    from examples.shared import make_gateway
except ImportError:  # browser layout: the file is copied in as demo_shared
    from demo_shared import make_gateway


@dataclass
class Ctx:
    request_id: str
    purpose: str
    delegator: str
    agent_id: str
    hops: int = 0


class UnguardedTarget:
    """Tools are called directly. No purpose check, no minimization, no sink
    rules, no approval, no consent check, no record."""

    name = "unguarded"

    def __init__(self, customers: Dict[str, dict]):
        self.customers = customers
        self.mem: Dict[str, Any] = {}
        self.sinks: Dict[str, List[str]] = {}
        self.attempts = 0
        self.records = 0

    def begin(self, request_id, purpose, delegator="rep-1", agent_id="agent-1"):
        return Ctx(request_id, purpose, delegator, agent_id)

    def lookup(self, ctx, sid) -> Optional[dict]:
        return dict(self.customers[sid])

    def write_points(self, ctx, sid, delta, approval=None) -> bool:
        self.customers[sid]["loyalty_points"] += delta
        return True

    def handoff(self, ctx, to_agent, purpose=None) -> Optional[Ctx]:
        return Ctx(ctx.request_id, purpose or ctx.purpose, ctx.delegator, to_agent, ctx.hops + 1)

    def emit(self, ctx, sink, text, sid, approval=None) -> Optional[str]:
        self.sinks.setdefault(sink, []).append(text)
        return text

    def remember(self, ctx, key, value):
        self.mem[key] = value

    def recall(self, ctx, key, from_request=None):
        return self.mem.get(key)

    def withdraw_consent(self, sid, purpose):
        pass  # nothing to withdraw from

    def record_stats(self):
        return {"attempts": 0, "records": 0, "chain_ok": None}


class GuardedTarget:
    """The same tools behind the purpose gateway."""

    name = "guarded"

    def __init__(self, customers: Dict[str, dict]):
        self.customers = customers
        self.gw = make_gateway(customers)
        self.attempts = 0

    def begin(self, request_id, purpose, delegator="rep-1", agent_id="agent-1"):
        return PurposePass(request_id, delegator, purpose, agent_id, "1")

    def lookup(self, ctx, sid) -> Optional[dict]:
        self.attempts += 1
        d = self.gw.call(ctx, "lookup_customer", sid)
        return d.data if d.allowed else None

    def write_points(self, ctx, sid, delta, approval=None) -> bool:
        self.attempts += 1
        return self.gw.call(ctx, "update_points", sid, approval=approval, delta=delta).allowed

    def handoff(self, ctx, to_agent, purpose=None):
        self.attempts += 1
        try:
            return self.gw.delegate(ctx, to_agent, purpose=purpose)
        except PolicyDenied:
            return None

    def emit(self, ctx, sink, text, sid, approval=None) -> Optional[str]:
        self.attempts += 1
        d = self.gw.emit(ctx, sink, text, sid, approval=approval)
        return d.data if d.allowed else None

    def remember(self, ctx, key, value):
        self.attempts += 1
        self.gw.remember(ctx, key, value)

    def recall(self, ctx, key, from_request=None):
        self.attempts += 1
        d = self.gw.recall(ctx, key, from_request_id=from_request)
        return d.data if d.allowed else None

    def withdraw_consent(self, sid, purpose):
        self.gw.registry.withdraw(subject_ref(sid, self.gw.salt), purpose)

    def record_stats(self):
        v = self.gw.ledger.verify()
        return {"attempts": self.attempts, "records": len(self.gw.ledger.entries), "chain_ok": v.ok}


_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE = re.compile(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b|\b\d{3}-\d{6}\b")


class ScannerTarget(UnguardedTarget):
    """A common fallback: tools are called directly, and a simple pattern
    scanner (emails and phone numbers) cleans text on its way out. It asks
    'does this text look like PII?'. It does not ask whose data it is, what
    the purpose is, or whether anyone approved. It is a deliberately simple
    baseline; a scanner with name recognition would catch more."""

    name = "scanner"

    def emit(self, ctx, sink, text, sid, approval=None):
        clean = _PHONE.sub("[PII]", _EMAIL.sub("[PII]", text))
        self.sinks.setdefault(sink, []).append(clean)
        return clean


class LayeredTarget(GuardedTarget):
    """Defense in depth: the gateway controls what the agent can read, do, and
    send, and the pattern scanner cleans text on its way out."""

    name = "layered"

    def emit(self, ctx, sink, text, sid, approval=None):
        clean = _PHONE.sub("[PII]", _EMAIL.sub("[PII]", text))
        return super().emit(ctx, sink, clean, sid, approval=approval)
