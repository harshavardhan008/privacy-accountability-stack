"""Reference purpose gateway: a checkpoint in front of every agent tool.

What it does on each call:
  1. checks the Purpose Pass carries a known purpose
  2. checks the tool and operation are allowed for that purpose
  3. checks the data subject has not withdrawn consent
  4. requires human approval where policy says so
  5. runs the tool, then removes every field the purpose does not need
  6. tracks which values were released, so output sinks can be checked
  7. writes an Action Record to the ledger, including for denials

It is a reference implementation for study and testing, not a production
security boundary. See docs/ARCHITECTURE.md for what it does not cover.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from .consent import ConsentRegistry
from .ledger import Ledger
from .record import ActionRecord, hash_value, subject_ref


class PolicyDenied(Exception):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class PurposePass:
    """The purpose of a request, carried with it through every tool call."""

    request_id: str
    delegator: str
    purpose: str
    agent_id: str
    agent_version: str = "1"
    environment: str = "production"
    hops: int = 0
    parent_record_id: Optional[str] = None


@dataclass
class ToolSpec:
    name: str
    operation: str  # read | write | send
    fn: Callable[..., dict]
    field_classes: Dict[str, str]  # output field -> data class
    destination: str = "internal"
    retention_days: int = 0
    requires_approval: Optional[bool] = None

    def needs_approval(self) -> bool:
        if self.requires_approval is not None:
            return self.requires_approval
        return self.operation in ("write", "send")


@dataclass
class SinkSpec:
    """Anywhere an agent can put text: a ticket, a vendor tool, a notes field."""

    name: str
    allowed_classes: Set[str]
    destination: str = "internal"  # internal | vendor | unclassified
    retention_days: int = 30
    requires_approval: Optional[bool] = None

    def needs_approval(self) -> bool:
        if self.requires_approval is not None:
            return self.requires_approval
        return self.destination != "internal"


@dataclass
class Decision:
    allowed: bool
    data: Any
    record: dict
    reason: str


class Gateway:
    def __init__(
        self,
        registry: ConsentRegistry,
        ledger: Ledger,
        tools: Dict[str, ToolSpec],
        sinks: Optional[Dict[str, SinkSpec]] = None,
        salt: str = "change-me",
        max_hops: int = 3,
    ):
        self.registry = registry
        self.ledger = ledger
        self.tools = tools
        self.sinks = sinks or {}
        self.salt = salt
        self.max_hops = max_hops
        self._released: Dict[str, List[Tuple[str, str]]] = {}
        self._last_record: Dict[str, str] = {}
        self._mem: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------------ helpers
    def _sref(self, subject_id: Optional[str]) -> Optional[str]:
        return subject_ref(subject_id, self.salt) if subject_id is not None else None

    def _write(
        self,
        p: PurposePass,
        *,
        tool: str,
        op: str,
        classes: List[str],
        decision: str,
        reason: str,
        dest: str = "internal",
        ret: int = 0,
        sref: Optional[str] = None,
        approval: Optional[str] = None,
        in_hash: str = "",
        out_hash: str = "",
    ) -> dict:
        record = ActionRecord(
            request_id=p.request_id,
            delegator=p.delegator,
            agent_id=p.agent_id,
            agent_version=p.agent_version,
            purpose=p.purpose,
            tool=tool,
            operation=op,
            data_classes=classes,
            consent_ref=self.registry.ref(p.purpose),
            approval=approval,
            destination=dest,
            retention_days=ret,
            decision=decision,
            reason=reason,
            environment=p.environment,
            subject_ref=sref,
            parent_record_id=self._last_record.get(p.request_id) or p.parent_record_id,
            input_hash=in_hash,
            output_hash=out_hash,
        )
        body = self.ledger.append(record)
        self._last_record[p.request_id] = body["record_id"]
        return body

    def _gate(self, p: PurposePass, spec_needs_approval: bool, operation: str, sref: Optional[str], approval: Optional[str]) -> Optional[str]:
        """Checks shared by tools and sinks. Returns a denial reason or None."""
        if p.purpose not in self.registry.purposes():
            return "unknown_purpose"
        if sref and self.registry.is_withdrawn(sref, p.purpose):
            return "consent_withdrawn"
        if p.environment == "shadow" and operation in ("write", "send"):
            return "shadow_proposal"
        if p.environment != "sandbox" and spec_needs_approval and not approval:
            return "approval_required"
        return None

    # -------------------------------------------------------------- tool calls
    def call(self, p: PurposePass, tool: str, subject_id: Optional[str] = None, approval: Optional[str] = None, **args) -> Decision:
        sref = self._sref(subject_id)
        in_hash = hash_value({"tool": tool, "args": args, "subject": sref})
        spec = self.tools.get(tool)

        def deny(reason: str, op: str = "read", dest: str = "internal", ret: int = 0) -> Decision:
            rec = self._write(p, tool=tool, op=op, classes=[], decision="deny", reason=reason,
                              dest=dest, ret=ret, sref=sref, approval=approval, in_hash=in_hash)
            return Decision(False, None, rec, reason)

        if spec is None:
            return deny("unknown_tool")
        op, dest, ret = spec.operation, spec.destination, spec.retention_days
        reason = self._gate(p, spec.needs_approval(), op, sref, approval)
        if reason is None and p.purpose in self.registry.purposes() and not self.registry.allows_tool(p.purpose, tool, op):
            reason = "tool_not_permitted_for_purpose"
        if reason:
            return deny(reason, op, dest, ret)

        raw = spec.fn(subject_id, **args) or {}
        kept = {
            k: v for k, v in raw.items()
            if self.registry.allows_class(p.purpose, spec.field_classes.get(k, "unclassified"))
        }
        dropped = len(raw) - len(kept)
        classes = sorted({spec.field_classes.get(k, "unclassified") for k in kept})
        released = self._released.setdefault(p.request_id, [])
        for k, v in kept.items():
            text = str(v)
            if len(text) >= 3:
                released.append((text, spec.field_classes.get(k, "unclassified")))
        decision = "minimized" if dropped else "allow"
        reason = f"dropped_{dropped}_fields" if dropped else "ok"
        rec = self._write(p, tool=tool, op=op, classes=classes, decision=decision, reason=reason,
                          dest=dest, ret=ret, sref=sref, approval=approval, in_hash=in_hash,
                          out_hash=hash_value(kept))
        return Decision(True, kept, rec, reason)

    # ------------------------------------------------------------------ sinks
    def emit(self, p: PurposePass, sink: str, text: str, subject_id: Optional[str] = None, approval: Optional[str] = None) -> Decision:
        """Let an agent put free text somewhere. Any value the gateway released
        earlier in this request is redacted if the sink may not hold its class."""
        sref = self._sref(subject_id)
        spec = self.sinks.get(sink)
        tool = f"sink:{sink}"
        in_hash = hash_value({"sink": sink, "text": text, "subject": sref})
        if spec is None:
            rec = self._write(p, tool=tool, op="write", classes=[], decision="deny", reason="unknown_sink",
                              sref=sref, approval=approval, in_hash=in_hash)
            return Decision(False, None, rec, "unknown_sink")
        op = "write" if spec.destination == "internal" else "send"
        reason = self._gate(p, spec.needs_approval(), op, sref, approval)
        if reason:
            rec = self._write(p, tool=tool, op=op, classes=[], decision="deny", reason=reason,
                              dest=spec.destination, ret=spec.retention_days, sref=sref,
                              approval=approval, in_hash=in_hash)
            return Decision(False, None, rec, reason)
        out, redacted = text, 0
        released = sorted(self._released.get(p.request_id, []), key=lambda t: -len(t[0]))
        for value, cls in released:
            if cls not in spec.allowed_classes and value in out:
                out = out.replace(value, f"[REDACTED:{cls}]")
                redacted += 1
        classes = sorted({cls for value, cls in released if cls in spec.allowed_classes and value in out})
        decision = "minimized" if redacted else "allow"
        reason = f"redacted_{redacted}_values" if redacted else "ok"
        rec = self._write(p, tool=tool, op=op, classes=classes, decision=decision, reason=reason,
                          dest=spec.destination, ret=spec.retention_days, sref=sref, approval=approval,
                          in_hash=in_hash, out_hash=hash_value(out))
        return Decision(True, out, rec, reason)

    # --------------------------------------------------------------- handoffs
    def delegate(self, p: PurposePass, to_agent_id: str, to_agent_version: str = "1", purpose: Optional[str] = None) -> PurposePass:
        """Hand work to another agent. The purpose travels along and cannot widen."""
        reason = None
        if purpose is not None and purpose != p.purpose:
            reason = "purpose_cannot_change_in_handoff"
        elif p.hops + 1 > self.max_hops:
            reason = "max_hops_exceeded"
        if reason:
            self._write(p, tool=f"handoff:{to_agent_id}", op="handoff", classes=[], decision="deny", reason=reason)
            raise PolicyDenied(reason)
        rec = self._write(p, tool=f"handoff:{to_agent_id}", op="handoff", classes=[], decision="allow", reason="ok")
        return replace(p, agent_id=to_agent_id, agent_version=to_agent_version, hops=p.hops + 1,
                       parent_record_id=rec["record_id"])

    # ----------------------------------------------------------------- memory
    def remember(self, p: PurposePass, key: str, value: Any) -> Decision:
        self._mem.setdefault(p.request_id, {})[key] = value
        rec = self._write(p, tool="memory:set", op="memory", classes=[], decision="allow", reason="ok",
                          in_hash=hash_value({"key": key}))
        return Decision(True, None, rec, "ok")

    def recall(self, p: PurposePass, key: str, from_request_id: Optional[str] = None) -> Decision:
        source = from_request_id or p.request_id
        if source != p.request_id:
            rec = self._write(p, tool="memory:get", op="memory", classes=[], decision="deny",
                              reason="cross_request_memory", in_hash=hash_value({"key": key, "from": source}))
            return Decision(False, None, rec, "cross_request_memory")
        value = self._mem.get(p.request_id, {}).get(key)
        rec = self._write(p, tool="memory:get", op="memory", classes=[], decision="allow", reason="ok",
                          in_hash=hash_value({"key": key}))
        return Decision(True, value, rec, "ok")

    def end_request(self, request_id: str) -> None:
        """Forget everything held for a finished request."""
        self._released.pop(request_id, None)
        self._mem.pop(request_id, None)
        self._last_record.pop(request_id, None)
