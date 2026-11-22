"""Tamper-evident, hash-chained ledger for Action Records.

Each entry commits to the one before it. Editing, deleting, or reordering an
entry breaks the chain. Truncating the tail, or rewriting the whole chain,
is only detectable if the head hash was anchored somewhere else (a ticket,
a signed email, another system). Pass that anchor as expected_head.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import List, Optional

from .record import ActionRecord, canonical, sha256_hex

GENESIS = "0" * 64


class LedgerError(Exception):
    pass


@dataclass
class VerifyResult:
    ok: bool
    index: Optional[int]
    message: str
    head: Optional[str] = None


def entry_hash(body: dict, prev: str) -> str:
    return sha256_hex(canonical({"body": body, "prev": prev}))


def verify_entries(entries: List[dict], expected_head: Optional[str] = None) -> VerifyResult:
    prev = GENESIS
    for i, e in enumerate(entries):
        if e.get("prev") != prev:
            return VerifyResult(False, i, "broken chain link")
        if entry_hash(e.get("body"), e.get("prev")) != e.get("hash"):
            return VerifyResult(False, i, "hash mismatch")
        prev = e["hash"]
    if expected_head is not None and prev != expected_head:
        return VerifyResult(False, len(entries), "head mismatch: entries were removed or added at the end", prev)
    return VerifyResult(True, None, "ok", prev)


class Ledger:
    def __init__(self, path: Optional[str] = None):
        self.path = path
        self.entries: List[dict] = []
        self.head = GENESIS
        if path and os.path.exists(path):
            self._load()

    def _load(self) -> None:
        with open(self.path, "r", encoding="utf-8") as fh:
            entries = [json.loads(line) for line in fh if line.strip()]
        result = verify_entries(entries)
        if not result.ok:
            raise LedgerError(f"ledger failed verification at entry {result.index}: {result.message}")
        self.entries = entries
        self.head = result.head or GENESIS

    def append(self, record: ActionRecord) -> dict:
        errors = record.validate()
        if errors:
            raise ValueError("invalid action record: " + "; ".join(errors))
        body = record.to_dict()
        h = entry_hash(body, self.head)
        entry = {"body": body, "prev": self.head, "hash": h}
        self.entries.append(entry)
        self.head = h
        if self.path:
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, sort_keys=True, ensure_ascii=False) + "\n")
        return body

    def bodies(self) -> List[dict]:
        return [e["body"] for e in self.entries]

    def verify(self, expected_head: Optional[str] = None) -> VerifyResult:
        return verify_entries(self.entries, expected_head)


def load_entries(path: str) -> List[dict]:
    with open(path, "r", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]
