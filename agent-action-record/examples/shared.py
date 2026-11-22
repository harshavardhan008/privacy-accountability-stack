"""Shared synthetic setup for the demos, the evaluation, and the tests.

Everything here is synthetic. No real customer data is used anywhere in this repo.
"""
from __future__ import annotations

import random
from typing import Dict, Optional, Tuple

from aar import (ConsentRegistry, Gateway, Ledger, PurposePolicy, SinkSpec, ToolSpec)

FIELD_CLASSES = {
    "name": "identity",
    "email": "contact",
    "phone": "contact",
    "loyalty_points": "account",
    "purchase_history": "behavioral",
    "card_last4": "financial",
    "address": "location",
    "birth_year": "demographic",
}

FIRST = ["Avery", "Jordan", "Riley", "Morgan", "Casey", "Taylor", "Quinn", "Rowan", "Sage", "Emerson"]
LAST = ["Stone", "Hayes", "Brooks", "Ellis", "Reed", "Wells", "Cole", "Frost", "Lane", "Pierce"]
ITEMS = ["oat milk", "batteries", "basil", "dish soap", "coffee beans", "paper towels", "yogurt", "rice"]


def make_customers(n: int = 200, seed: int = 2026) -> Dict[str, dict]:
    rng = random.Random(seed)
    customers = {}
    for i in range(n):
        first, last = rng.choice(FIRST), rng.choice(LAST)
        sid = f"cust-{i:04d}"
        customers[sid] = {
            "name": f"{first} {last} {i:04d}",
            "email": f"{first}.{last}.{i:04d}@example.test".lower(),
            "phone": f"555-01{i:04d}",
            "loyalty_points": 1000 + rng.randint(0, 8999),
            "purchase_history": "; ".join(rng.sample(ITEMS, 3)) + f" (order {i:04d})",
            "card_last4": f"card ending {rng.randint(1000, 9999)}-{i:04d}",
            "address": f"{rng.randint(10, 999)} Maple St unit {i:04d}",
            "birth_year": f"born {rng.randint(1950, 2004)}-{i:04d}",
        }
    return customers


def make_registry() -> ConsentRegistry:
    return ConsentRegistry(
        {
            "loyalty_support": PurposePolicy(
                "loyalty_support", {"identity", "account"},
                {"lookup_customer": {"read"}, "update_points": {"write"}}),
            "order_status": PurposePolicy(
                "order_status", {"identity", "location"}, {"lookup_customer": {"read"}}),
            "fraud_review": PurposePolicy(
                "fraud_review", {"identity", "account", "financial", "behavioral"},
                {"lookup_customer": {"read"}}),
        },
        version="v1",
    )


def make_gateway(customers: Dict[str, dict], ledger_path: Optional[str] = None) -> Gateway:
    def lookup_customer(subject_id, **_):
        return dict(customers[subject_id])

    def update_points(subject_id, delta=0, **_):
        customers[subject_id]["loyalty_points"] += delta
        return {"loyalty_points": customers[subject_id]["loyalty_points"]}

    tools = {
        "lookup_customer": ToolSpec("lookup_customer", "read", lookup_customer, FIELD_CLASSES),
        "update_points": ToolSpec("update_points", "write", update_points, {"loyalty_points": "account"}),
    }
    sinks = {
        "ticket_system": SinkSpec("ticket_system", {"identity", "account"}, "internal"),
        "vendor_helpdesk": SinkSpec("vendor_helpdesk", {"account"}, "vendor"),
        "notes_unclassified": SinkSpec("notes_unclassified", set(), "unclassified"),
    }
    return Gateway(make_registry(), Ledger(ledger_path), tools, sinks, salt="demo-salt")
