"""The opening story from the talk: a support agent fixes missing loyalty points.

Run:  python examples/loyalty_points_demo.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from aar import PolicyDenied, PurposePass, subject_ref  # noqa: E402
from aar import ladder, lineage  # noqa: E402
from examples.shared import make_customers, make_gateway  # noqa: E402


def show(label, decision):
    print(f"  {label:<44} -> {decision.record['decision']:<9} {decision.reason}")


def main():
    customers = make_customers(20)
    gw = make_gateway(customers)
    sid = "cust-0003"
    p = PurposePass("req-001", "support-rep-17", "loyalty_support", "support-agent", "1.4")

    print("1. The agent looks up the customer (it asks for everything)")
    d_lookup = gw.call(p, "lookup_customer", sid)
    d = d_lookup
    show("lookup_customer", d)
    print("     agent receives only:", sorted(d.data))

    print("2. The agent tries to add points without a person approving")
    show("update_points (no approval)", gw.call(p, "update_points", sid, delta=250))
    show("update_points (approved by rep)", gw.call(p, "update_points", sid, approval="support-rep-17", delta=250))

    print("3. The agent hands the case to a fraud agent, quietly widening the purpose")
    try:
        gw.delegate(p, "fraud-agent", purpose="fraud_review")
    except PolicyDenied as exc:
        print(f"  handoff with new purpose            -> deny      {exc.reason}")
    child = gw.delegate(p, "billing-agent")
    print("  handoff with same purpose           -> allow     purpose travels along:", child.purpose)

    print("4. The agent writes what it learned into a ticket (internal)")
    summary = f"Customer {d_lookup.data['name']} has {d_lookup.data['loyalty_points']} points."
    d = gw.emit(p, "ticket_system", summary, sid)
    show("ticket_system (internal)", d)
    print("     stored text:", d.data)

    print("   A fraud review on another case pastes everything into a vendor tool")
    p2 = PurposePass("req-002", "fraud-analyst-4", "fraud_review", "fraud-agent", "2.0")
    info = gw.call(p2, "lookup_customer", "cust-0007").data
    text = "Review notes: " + " | ".join(str(v) for v in info.values())
    d = gw.emit(p2, "vendor_helpdesk", text, "cust-0007", approval="fraud-analyst-4")
    show("vendor_helpdesk (external)", d)
    print("     stored text:", d.data)

    print("5. The customer withdraws consent. Where did their data go?")
    sref = subject_ref(sid, gw.salt)
    gw.registry.withdraw(sref, "loyalty_support")
    show("lookup_customer after withdrawal", gw.call(p, "lookup_customer", sid))
    for r in lineage.withdrawal_impact(gw.ledger.bodies(), sref):
        print(f"     to review: {r['tool']:<16} classes={','.join(r['data_classes']) or '-'}  destination={r['destination']}")

    print("6. The audit trail")
    for n in lineage.trace(gw.ledger.bodies(), "req-001"):
        print(f"  {'  ' * n['depth']}{n['tool']:<24} {n['decision']:<9} {','.join(n['data_classes']) or '-'}")
    result = gw.ledger.verify()
    print(f"  ledger chain: {result.message}, head={result.head[:16]}...")
    grad = ladder.evaluate(gw.ledger.bodies(), "production")
    print("  ladder:", "top rung" if grad.next is None else grad.next)


if __name__ == "__main__":
    main()
