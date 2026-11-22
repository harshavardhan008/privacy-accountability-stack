"""The Action Record: the minimum record written for every agent action.

Nine content fields (request, delegator, agent, purpose, tool and operation,
data classes, consent reference, approval, destination and retention) plus
context and integrity fields. Personal data values are never stored here,
only data classes and hashes.
"""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, List, Optional

OPERATIONS = ("read", "write", "send", "handoff", "memory")
DECISIONS = ("allow", "minimized", "deny")
ENVIRONMENTS = ("sandbox", "shadow", "limited", "production")


def canonical(obj: Any) -> bytes:
    """Deterministic JSON bytes used for hashing."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex(data) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def hash_value(value: Any) -> str:
    return sha256_hex(canonical(value))


def subject_ref(subject_id: str, salt: str) -> str:
    """Salted, truncated hash of a data subject id. Lets you answer
    'which actions touched this person' without storing the id."""
    return sha256_hex(f"{salt}:{subject_id}")[:16]


@dataclass
class ActionRecord:
    # nine content fields
    request_id: str
    delegator: str
    agent_id: str
    agent_version: str
    purpose: str
    tool: str
    operation: str
    data_classes: List[str]
    consent_ref: str
    approval: Optional[str]
    destination: str
    retention_days: int
    # context and integrity fields
    decision: str
    reason: str
    environment: str = "production"
    subject_ref: Optional[str] = None
    parent_record_id: Optional[str] = None
    input_hash: str = ""
    output_hash: str = ""
    record_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return asdict(self)

    def validate(self) -> List[str]:
        errors: List[str] = []
        if not self.request_id:
            errors.append("request_id is required")
        if not self.delegator:
            errors.append("delegator is required")
        if not self.agent_id:
            errors.append("agent_id is required")
        if not self.purpose:
            errors.append("purpose is required")
        if not self.tool:
            errors.append("tool is required")
        if self.operation not in OPERATIONS:
            errors.append(f"operation must be one of {OPERATIONS}")
        if self.decision not in DECISIONS:
            errors.append(f"decision must be one of {DECISIONS}")
        if self.environment not in ENVIRONMENTS:
            errors.append(f"environment must be one of {ENVIRONMENTS}")
        if not isinstance(self.data_classes, list) or not all(isinstance(c, str) for c in self.data_classes):
            errors.append("data_classes must be a list of strings")
        if not self.consent_ref:
            errors.append("consent_ref is required")
        if not isinstance(self.retention_days, int) or self.retention_days < 0:
            errors.append("retention_days must be a non-negative integer")
        return errors


def validate_dict(body: dict) -> List[str]:
    """Validate a record loaded from JSON."""
    try:
        return ActionRecord(**body).validate()
    except TypeError as exc:  # missing or unknown fields
        return [str(exc)]
