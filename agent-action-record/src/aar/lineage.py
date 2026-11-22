"""Action lineage: answer 'what did this request do' and 'who was touched'."""
from __future__ import annotations

from collections import Counter
from typing import Dict, List, Optional


def trace(records: List[dict], request_id: str) -> List[dict]:
    """Actions of one request, in ledger order. depth counts the accepted
    handoffs between the start of the request and each action."""
    mine = [r for r in records if r["request_id"] == request_id]
    by_id = {r["record_id"]: r for r in mine}
    out = []
    for r in mine:
        depth, cur, seen = 0, r, set()
        while cur.get("parent_record_id") in by_id and cur["record_id"] not in seen:
            seen.add(cur["record_id"])
            cur = by_id[cur["parent_record_id"]]
            if cur["operation"] == "handoff" and cur["decision"] == "allow":
                depth += 1
        out.append({**r, "depth": depth})
    return out


def subject_actions(records: List[dict], sref: str) -> List[dict]:
    return [r for r in records if r.get("subject_ref") == sref]


def exposure_by_class(records: List[dict], request_id: Optional[str] = None) -> Dict[str, int]:
    """How many allowed actions exposed each data class."""
    counter: Counter = Counter()
    for r in records:
        if request_id and r["request_id"] != request_id:
            continue
        if r["decision"] == "deny":
            continue
        counter.update(r["data_classes"])
    return dict(counter)


def withdrawal_impact(records: List[dict], sref: str, purpose: Optional[str] = None) -> List[dict]:
    """Actions that released data about a subject. Start here when a subject
    withdraws consent: these are the places data may need to be unwound."""
    hits = [r for r in subject_actions(records, sref) if r["decision"] != "deny" and r["data_classes"]]
    if purpose:
        hits = [r for r in hits if r["purpose"] == purpose]
    return hits


def to_dot(records: List[dict], request_id: str) -> str:
    nodes = trace(records, request_id)
    lines = ["digraph lineage {", "  rankdir=LR;", "  node [shape=box,fontname=Helvetica];"]
    ids = {n["record_id"] for n in nodes}
    for n in nodes:
        label = f'{n["tool"]}\\n{n["decision"]}'
        if n["data_classes"]:
            label += "\\n" + ",".join(n["data_classes"])
        color = "red" if n["decision"] == "deny" else ("orange" if n["decision"] == "minimized" else "black")
        lines.append(f'  "{n["record_id"]}" [label="{label}",color={color}];')
    for n in nodes:
        if n.get("parent_record_id") in ids:
            lines.append(f'  "{n["parent_record_id"]}" -> "{n["record_id"]}";')
    lines.append("}")
    return "\n".join(lines)
