"""Synthetic evaluation of the reference gateway against a naive baseline.

Four leak scenarios, utility check, tamper-evidence test, and overhead.
All data is synthetic and the seed is fixed. Run:  python bench/evaluate.py
Writes results/evaluation.json and results/evaluation.md.
"""
from __future__ import annotations

import copy
import json
import os
import platform
import random
import sys
import time

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

from aar import Ledger, PolicyDenied, PurposePass  # noqa: E402
from aar.ledger import entry_hash, verify_entries  # noqa: E402
from examples.shared import FIELD_CLASSES, make_customers, make_gateway  # noqa: E402

N = 200
SINK_ALLOWED = {"ticket_system": {"identity", "account"}, "vendor_helpdesk": {"account"}, "notes_unclassified": set()}
APPROVER = "supervisor-1"


def leaked_values(text, cust, allowed):
    """Ground truth: values in text whose class the sink may not hold."""
    return sum(1 for f, cls in FIELD_CLASSES.items() if cls not in allowed and str(cust[f]) in text)


def scenario_a(customers):
    """Wide tool scope."""
    gw = make_gateway(customers)
    needed = {"name", "loyalty_points"}
    naive_excess = gw_excess = delivered = denials = 0
    for i in range(N):
        sid = f"cust-{i:04d}"
        raw = customers[sid]
        naive_excess += len(set(raw) - needed)
        d = gw.call(PurposePass(f"a-{i}", "rep", "loyalty_support", "agent"), "lookup_customer", sid)
        denials += 0 if d.allowed else 1
        gw_excess += len(set(d.data) - needed)
        delivered += 1 if needed <= set(d.data) else 0
    return {
        "naive_excess_fields_per_call": naive_excess / N,
        "gateway_excess_fields_per_call": gw_excess / N,
        "needed_fields_delivered_pct": 100 * delivered / N,
        "legitimate_requests_denied": denials,
    }


def scenario_b(customers):
    """Context carry-over through a shared agent memory."""
    gw = make_gateway(customers)
    shared_mem, naive_exposed, gw_exposed, gw_denied = {}, 0, 0, 0
    for i in range(N):
        sid = f"cust-{i:04d}"
        c = customers[sid]
        # naive: a long-lived memory store shared across requests
        previous = shared_mem.get("last_customer")
        if previous and previous != c["email"]:
            naive_exposed += 1
        shared_mem["last_customer"] = c["email"]
        # gateway: memory is scoped to the request
        p = PurposePass(f"b-{i}", "rep", "loyalty_support", "agent")
        if i > 0:
            d = gw.recall(p, "last_customer", from_request_id=f"b-{i-1}")
            gw_denied += 0 if d.allowed else 1
            if d.allowed and d.data:
                gw_exposed += 1
        gw.remember(p, "last_customer", c["email"])
        own = gw.recall(p, "last_customer")
        assert own.allowed and own.data == c["email"]
    return {"naive_requests_exposed_to_other_customer": naive_exposed,
            "gateway_requests_exposed_to_other_customer": gw_exposed,
            "gateway_cross_request_reads_denied": gw_denied,
            "requests": N}


def scenario_c(customers):
    """Summaries as new copies: the same agent writes a summary to three sinks."""
    gw = make_gateway(customers)
    naive = {s: 0 for s in SINK_ALLOWED}
    gated = {s: 0 for s in SINK_ALLOWED}
    redactions = {s: 0 for s in SINK_ALLOWED}
    for i in range(N):
        sid = f"cust-{i:04d}"
        c = customers[sid]
        # Naive agent: sees every field, writes all of it into the summary.
        naive_text = "Case summary. " + " | ".join(str(v) for v in c.values())
        for s, allowed in SINK_ALLOWED.items():
            naive[s] += leaked_values(naive_text, c, allowed)
        # Gateway agent under fraud_review: sees only what that purpose needs.
        p = PurposePass(f"c-{i}", "rep", "fraud_review", "agent")
        d = gw.call(p, "lookup_customer", sid)
        text = "Case summary. " + " | ".join(str(v) for v in d.data.values())
        for s, allowed in SINK_ALLOWED.items():
            out = gw.emit(p, s, text, sid, approval=APPROVER)
            gated[s] += leaked_values(out.data, c, allowed)
            redactions[s] += int(out.reason.split("_")[1]) if out.reason.startswith("redacted_") else 0
    return {
        "naive_leaked_values_per_summary": {s: v / N for s, v in naive.items()},
        "gateway_leaked_values_per_summary": {s: v / N for s, v in gated.items()},
        "sink_redactions_per_summary": {s: v / N for s, v in redactions.items()},
    }


def scenario_d(customers):
    """Lost purpose in handoffs: half benign, half widening."""
    gw = make_gateway(customers)
    benign_ok = widened_ok = widened_denied = 0
    for i in range(N):
        p = PurposePass(f"d-{i}", "rep", "loyalty_support", "agent-a")
        if i % 2 == 0:
            gw.delegate(p, "agent-b")
            benign_ok += 1
        else:
            try:
                gw.delegate(p, "agent-b", purpose="fraud_review")
                widened_ok += 1
            except PolicyDenied:
                widened_denied += 1
    total_w = N // 2
    return {"naive_widened_handoffs_accepted_pct": 100.0,
            "gateway_widened_handoffs_accepted_pct": 100 * widened_ok / total_w,
            "gateway_widened_handoffs_denied": widened_denied,
            "gateway_benign_handoffs_accepted": benign_ok, "benign_handoffs": N // 2}


def build_ledger(customers, n_entries=500):
    gw = make_gateway(customers)
    i = 0
    while len(gw.ledger.entries) < n_entries:
        p = PurposePass(f"t-{i}", "rep", "loyalty_support", "agent")
        gw.call(p, "lookup_customer", f"cust-{i % N:04d}")
        gw.call(p, "update_points", f"cust-{i % N:04d}", delta=1)  # denied: no approval
        i += 1
    return gw.ledger.entries[:n_entries]


def rechain(entries, start):
    prev = entries[start - 1]["hash"] if start > 0 else "0" * 64
    for e in entries[start:]:
        e["prev"] = prev
        e["hash"] = entry_hash(e["body"], prev)
        prev = e["hash"]


def tamper_test(customers, trials=200, seed=7):
    rng = random.Random(seed)
    base = build_ledger(customers)
    head = base[-1]["hash"]
    kinds = ["edit_field", "delete_middle", "swap_two", "truncate_tail", "rewrite_chain"]
    out = {k: {"trials": trials, "detected_without_anchor": 0, "detected_with_anchor": 0} for k in kinds}
    for kind in kinds:
        for _ in range(trials):
            e = copy.deepcopy(base)
            if kind == "edit_field":
                i = rng.randrange(len(e))
                f = rng.choice(["decision", "purpose", "reason", "data_classes", "approval"])
                e[i]["body"][f] = ["tampered"] if f == "data_classes" else "tampered"
            elif kind == "delete_middle":
                del e[rng.randrange(1, len(e) - 1)]
            elif kind == "swap_two":
                i = rng.randrange(0, len(e) - 1)
                e[i], e[i + 1] = e[i + 1], e[i]
            elif kind == "truncate_tail":
                del e[-rng.randint(1, 10):]
            else:  # edit then recompute every hash after the edit
                i = rng.randrange(len(e))
                e[i]["body"]["decision"] = "allow" if e[i]["body"]["decision"] == "deny" else "deny"
                rechain(e, i)
            if not verify_entries(e).ok:
                out[kind]["detected_without_anchor"] += 1
            if not verify_entries(e, expected_head=head).ok:
                out[kind]["detected_with_anchor"] += 1
    return out


def overhead(customers, calls=20000):
    gw = make_gateway(customers)
    p = PurposePass("bench", "rep", "loyalty_support", "agent")
    tool = gw.tools["lookup_customer"].fn
    t0 = time.perf_counter()
    for i in range(calls):
        tool(f"cust-{i % N:04d}")
    direct = (time.perf_counter() - t0) / calls * 1e6
    t0 = time.perf_counter()
    for i in range(calls):
        gw.call(p, "lookup_customer", f"cust-{i % N:04d}")
    mem = (time.perf_counter() - t0) / calls * 1e6
    path = os.path.join(ROOT, "results", "_bench_ledger.jsonl")
    if os.path.exists(path):
        os.remove(path)
    gw2 = make_gateway(customers, ledger_path=path)
    t0 = time.perf_counter()
    for i in range(calls):
        gw2.call(p, "lookup_customer", f"cust-{i % N:04d}")
    disk = (time.perf_counter() - t0) / calls * 1e6
    os.remove(path)
    return {"calls": calls, "direct_tool_us": round(direct, 1), "gateway_memory_ledger_us": round(mem, 1),
            "gateway_file_ledger_us": round(disk, 1),
            "python": platform.python_version(), "machine": platform.machine()}


def main():
    customers = make_customers(N)
    res = {
        "setup": {"synthetic_customers": N, "fields_per_customer": len(FIELD_CLASSES), "seed": 2026},
        "A_wide_tool_scope": scenario_a(copy.deepcopy(customers)),
        "B_context_carry_over": scenario_b(copy.deepcopy(customers)),
        "C_summaries_as_copies": scenario_c(copy.deepcopy(customers)),
        "D_lost_purpose_handoff": scenario_d(copy.deepcopy(customers)),
        "tamper_evidence": tamper_test(copy.deepcopy(customers)),
        "overhead": overhead(copy.deepcopy(customers)),
    }
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    with open(os.path.join(ROOT, "results", "evaluation.json"), "w") as fh:
        json.dump(res, fh, indent=2)
    a, b, c, d, t, o = (res[k] for k in ["A_wide_tool_scope", "B_context_carry_over", "C_summaries_as_copies",
                                          "D_lost_purpose_handoff", "tamper_evidence", "overhead"])
    md = [
        "# Evaluation results (synthetic data, fixed seed)", "",
        f"{N} synthetic customers, {len(FIELD_CLASSES)} fields each. Naive baseline = direct tool access, shared agent memory, unfiltered output.", "",
        "| Scenario | Measure | Naive | Gateway |", "|---|---|---|---|",
        f"| A. Wide tool scope | Fields beyond purpose need, per call | {a['naive_excess_fields_per_call']:.1f} | {a['gateway_excess_fields_per_call']:.1f} |",
        f"| B. Context carry-over | Requests exposed to another customer's data | {b['naive_requests_exposed_to_other_customer']} of {N} | {b['gateway_requests_exposed_to_other_customer']} of {N} |",
    ]
    for s in SINK_ALLOWED:
        md.append(f"| C. Summary copies | Disallowed values in {s}, per summary | {c['naive_leaked_values_per_summary'][s]:.1f} | {c['gateway_leaked_values_per_summary'][s]:.1f} |")
    md += [
        f"| D. Lost purpose | Purpose-widening handoffs accepted | {d['naive_widened_handoffs_accepted_pct']:.0f}% | {d['gateway_widened_handoffs_accepted_pct']:.0f}% |",
        "", f"Utility: needed fields delivered {a['needed_fields_delivered_pct']:.0f}%; legitimate requests denied {a['legitimate_requests_denied']}; benign handoffs accepted {d['gateway_benign_handoffs_accepted']} of {d['benign_handoffs']}.", "",
        "| Tamper type | Detected, chain only | Detected, with anchored head |", "|---|---|---|",
    ]
    for k, v in t.items():
        md.append(f"| {k} | {100*v['detected_without_anchor']/v['trials']:.0f}% | {100*v['detected_with_anchor']/v['trials']:.0f}% |")
    md += ["", f"Overhead per call ({o['calls']} calls, Python {o['python']}, {o['machine']}): direct tool {o['direct_tool_us']} us, gateway with in-memory ledger {o['gateway_memory_ledger_us']} us, gateway with file ledger {o['gateway_file_ledger_us']} us.", ""]
    with open(os.path.join(ROOT, "results", "evaluation.md"), "w") as fh:
        fh.write("\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main()
