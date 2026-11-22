"""agent-action-record: purpose-aware accountability for AI agents that touch personal data."""
from .consent import ConsentRegistry, PurposePolicy
from .gateway import Decision, Gateway, PolicyDenied, PurposePass, SinkSpec, ToolSpec
from .ledger import Ledger, LedgerError, VerifyResult, verify_entries
from .record import ActionRecord, subject_ref

__version__ = "0.1.0"
__all__ = [
    "ActionRecord", "ConsentRegistry", "Decision", "Gateway", "Ledger", "LedgerError",
    "PolicyDenied", "PurposePass", "PurposePolicy", "SinkSpec", "ToolSpec", "VerifyResult",
    "subject_ref", "verify_entries",
]
