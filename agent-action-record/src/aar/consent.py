"""Consent and purpose registry.

A registry maps each controlled purpose to the data classes it may see and
the tool operations it may perform. It also tracks subjects who withdrew
consent. Real deployments would back this with a consent management system;
this class is the interface the gateway needs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Set, Tuple


@dataclass
class PurposePolicy:
    purpose: str
    allowed_classes: Set[str]
    allowed_tools: Dict[str, Set[str]] = field(default_factory=dict)  # tool -> {operations}


class ConsentRegistry:
    def __init__(self, policies: Dict[str, PurposePolicy], version: str = "v1"):
        self.policies = policies
        self.version = version
        self._withdrawn: Set[Tuple[str, Optional[str]]] = set()

    def purposes(self) -> Set[str]:
        return set(self.policies)

    def ref(self, purpose: str) -> str:
        return f"consent:{self.version}:{purpose}"

    def allows_class(self, purpose: str, data_class: str) -> bool:
        policy = self.policies.get(purpose)
        return bool(policy) and data_class in policy.allowed_classes

    def allows_tool(self, purpose: str, tool: str, operation: str) -> bool:
        policy = self.policies.get(purpose)
        return bool(policy) and operation in policy.allowed_tools.get(tool, set())

    def withdraw(self, subject_ref: str, purpose: Optional[str] = None) -> None:
        """purpose=None withdraws consent for every purpose."""
        self._withdrawn.add((subject_ref, purpose))

    def is_withdrawn(self, subject_ref: Optional[str], purpose: str) -> bool:
        if subject_ref is None:
            return False
        return (subject_ref, None) in self._withdrawn or (subject_ref, purpose) in self._withdrawn
