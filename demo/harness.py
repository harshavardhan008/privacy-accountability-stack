"""Browser harness for the live demo. Runs the real agent-action-record code.

Each step returns a plain dict that the page turns into cards. All data is
synthetic. Nothing leaves the browser.
"""
from __future__ import annotations

import copy
import json

from aar import PolicyDenied, PurposePass, subject_ref
from aar import ladder, lineage
from aar.ledger import verify_entries
from demo_shared import FIELD_CLASSES, make_customers, make_gateway

SID = "cust-0003"
STEPS = 6


def ev(label, decision, reason, tool=None, classes=None):
    return {"label": label, "decision": decision, "reason": reason,
            "classes": classes or [], "tool": tool}


class Demo:
    def __init__(self):
        self.reset()

    def reset(self):
        self.customers = make_customers(20)
        self.gw = make_gateway(self.customers)
        self.p = PurposePass("req-001", "support-rep-17", "loyalty_support", "support-agent", "1.4")
        self.lookup = None
        self.sref = subject_ref(SID, self.gw.salt)
        self.done = 0

    # ---------------------------------------------------------------- steps
    def step(self, n):
        if n != self.done + 1:
            return {"error": f"run step {self.done + 1} first"}
        out = getattr(self, f"_s{n}")()
        self.done = n
        return out

    def _s1(self):
        d = self.gw.call(self.p, "lookup_customer", SID)
        self.lookup = d
        everything = list(FIELD_CLASSES)
        released = sorted(d.data)
        withheld = [{"field": f, "class": FIELD_CLASSES[f]} for f in everything if f not in d.data]
        return {
            "events": [ev("lookup_customer", d.record["decision"], d.reason, "lookup_customer", d.record["data_classes"])],
            "asked": everything, "released": released, "withheld": withheld,
            "released_data": d.data,
            "note": "The agent asked for the whole customer record. The purpose (loyalty_support) only needs identity and account data, so the gateway removed the rest before the agent saw it.",
        }

    def _s2(self):
        a = self.gw.call(self.p, "update_points", SID, delta=250)
        b = self.gw.call(self.p, "update_points", SID, approval="support-rep-17", delta=250)
        return {
            "events": [
                ev("update_points, no approval", a.record["decision"], a.reason, "update_points"),
                ev("update_points, approved by the rep", b.record["decision"], b.reason, "update_points", b.record["data_classes"]),
            ],
            "note": "Writes need a named person's approval. The denied attempt is still recorded.",
        }

    def _s3(self):
        events = []
        try:
            self.gw.delegate(self.p, "fraud-agent", purpose="fraud_review")
        except PolicyDenied as exc:
            events.append(ev("hand off to the fraud agent with a wider purpose", "deny", exc.reason, "handoff:fraud-agent"))
        child = self.gw.delegate(self.p, "billing-agent")
        events.append(ev("hand off to the billing agent with the same purpose", "allow", "ok", "handoff:billing-agent"))
        return {
            "events": events,
            "note": f"The purpose travels with the work and cannot widen. The billing agent still carries: {child.purpose}.",
        }

    def _s4(self):
        data = self.lookup.data
        summary = f"Customer {data['name']} has {data['loyalty_points']} points."
        d1 = self.gw.emit(self.p, "ticket_system", summary, SID)
        p2 = PurposePass("req-002", "fraud-analyst-4", "fraud_review", "fraud-agent", "2.0")
        info = self.gw.call(p2, "lookup_customer", "cust-0007").data
        text = "Review notes: " + " | ".join(str(v) for v in info.values())
        d2 = self.gw.emit(p2, "vendor_helpdesk", text, "cust-0007", approval="fraud-analyst-4")
        return {
            "events": [
                ev("summary into the internal ticket", d1.record["decision"], d1.reason, "sink:ticket_system", d1.record["data_classes"]),
                ev("fraud notes pasted into a vendor tool", d2.record["decision"], d2.reason, "sink:vendor_helpdesk", d2.record["data_classes"]),
            ],
            "stored": [
                {"where": "Internal ticket", "text": d1.data},
                {"where": "Vendor helpdesk (external)", "text": d2.data},
            ],
            "note": "A summary is a new copy of personal data. The gateway tracks what it released and redacts any value the destination may not hold.",
        }

    def _s5(self):
        self.gw.registry.withdraw(self.sref, "loyalty_support")
        d = self.gw.call(self.p, "lookup_customer", SID)
        impact = lineage.withdrawal_impact(self.gw.ledger.bodies(), self.sref)
        return {
            "events": [ev("lookup after consent withdrawn", d.record["decision"], d.reason, "lookup_customer")],
            "impact": [{"tool": r["tool"], "classes": r["data_classes"], "destination": r["destination"]} for r in impact],
            "note": "The customer withdrew consent. The next lookup is denied, and the ledger lists every earlier action that released their data, so you know what to unwind.",
        }

    def _s6(self):
        bodies = self.gw.ledger.bodies()
        rows = [{"depth": n["depth"], "tool": n["tool"], "decision": n["decision"], "classes": n["data_classes"]}
                for n in lineage.trace(bodies, "req-001")]
        v = self.gw.ledger.verify()
        g = ladder.evaluate(bodies, "production")
        return {
            "events": [],
            "trace": rows,
            "chain": {"ok": v.ok, "message": v.message, "head": v.head, "length": len(bodies)},
            "ladder": "top rung" if g.next is None else g.next,
            "note": "One record per action, including denials. Each record stores data classes and hashes, never the values themselves.",
        }

    # --------------------------------------------------------------- ledger
    def ledger_view(self):
        out = []
        for i, e in enumerate(self.gw.ledger.entries):
            b = e["body"]
            out.append({"i": i, "request": b["request_id"], "tool": b["tool"], "purpose": b["purpose"],
                        "decision": b["decision"], "reason": b["reason"], "classes": b["data_classes"],
                        "hash": e["hash"][:10], "body": b})
        return out

    def tamper(self, kind):
        entries = copy.deepcopy(self.gw.ledger.entries)
        head = self.gw.ledger.head
        if len(entries) < 3:
            return {"error": "run a few steps first"}
        if kind == "edit":
            entries[1]["body"]["purpose"] = "fraud_review"
            r = verify_entries(entries)
            what = "Changed the purpose on record 2 from loyalty_support to fraud_review."
        elif kind == "delete":
            del entries[1]
            r = verify_entries(entries)
            what = "Deleted record 2."
        else:
            entries = entries[:-1]
            r1 = verify_entries(entries)
            r2 = verify_entries(entries, expected_head=head)
            return {"what": "Cut the last record off the end.",
                    "without_anchor": {"ok": r1.ok, "message": r1.message},
                    "with_anchor": {"ok": r2.ok, "message": r2.message}}
        return {"what": what, "result": {"ok": r.ok, "message": r.message, "index": r.index}}


_demo = Demo()


def run(op, arg=None):
    """Single entry point for the page. Returns a JSON string."""
    if op == "reset":
        _demo.reset()
        return json.dumps({"ok": True})
    if op == "step":
        return json.dumps(_demo.step(int(arg)))
    if op == "ledger":
        return json.dumps(_demo.ledger_view())
    if op == "tamper":
        return json.dumps(_demo.tamper(arg))
    return json.dumps({"error": "unknown op"})
