import copy
import json
import os
import sys

import pytest

from aar import ActionRecord, Ledger, LedgerError, PolicyDenied, PurposePass, subject_ref, verify_entries
from aar import ladder, lineage, scorecard
from aar.ledger import entry_hash
from aar.record import validate_dict
from examples.shared import make_customers, make_gateway


@pytest.fixture()
def gw():
    return make_gateway(make_customers(30))


def P(purpose="loyalty_support", env="production", rid="r1"):
    return PurposePass(rid, "rep-1", purpose, "agent", "1", environment=env)


# ---------------------------------------------------------------- record
def test_record_validation_catches_bad_fields():
    rec = ActionRecord("", "d", "a", "1", "p", "t", "teleport", ["x"], "c", None, "internal", -1, "maybe", "r")
    errors = rec.validate()
    assert any("request_id" in e for e in errors)
    assert any("operation" in e for e in errors)
    assert any("decision" in e for e in errors)
    assert any("retention_days" in e for e in errors)


def test_validate_dict_flags_unknown_fields():
    assert validate_dict({"bogus": 1})


# ---------------------------------------------------------------- gateway
def test_minimization_drops_fields_the_purpose_does_not_need(gw):
    d = gw.call(P(), "lookup_customer", "cust-0001")
    assert d.allowed and d.record["decision"] == "minimized"
    assert set(d.data) == {"name", "loyalty_points"}
    assert d.record["data_classes"] == ["account", "identity"]


def test_unknown_purpose_tool_and_disallowed_tool_are_denied(gw):
    assert gw.call(P("made_up"), "lookup_customer", "cust-0001").reason == "unknown_purpose"
    assert gw.call(P(), "no_such_tool", "cust-0001").reason == "unknown_tool"
    assert gw.call(P("order_status"), "update_points", "cust-0001", approval="x", delta=1).reason == "tool_not_permitted_for_purpose"


def test_denials_are_recorded_too(gw):
    gw.call(P(), "update_points", "cust-0001", delta=5)
    last = gw.ledger.bodies()[-1]
    assert last["decision"] == "deny" and last["reason"] == "approval_required"


def test_write_needs_approval_outside_sandbox_only(gw):
    assert gw.call(P(), "update_points", "cust-0002", delta=5).reason == "approval_required"
    assert gw.call(P(), "update_points", "cust-0002", approval="rep-1", delta=5).allowed
    assert gw.call(P(env="sandbox"), "update_points", "cust-0002", delta=5).allowed


def test_shadow_mode_turns_writes_into_proposals(gw):
    d = gw.call(P(env="shadow"), "update_points", "cust-0003", approval="rep-1", delta=5)
    assert not d.allowed and d.reason == "shadow_proposal"


def test_withdrawn_consent_blocks_that_purpose_only(gw):
    sref = subject_ref("cust-0004", gw.salt)
    gw.registry.withdraw(sref, "loyalty_support")
    assert gw.call(P(), "lookup_customer", "cust-0004").reason == "consent_withdrawn"
    assert gw.call(P("order_status"), "lookup_customer", "cust-0004").allowed
    gw.registry.withdraw(sref)  # all purposes
    assert gw.call(P("order_status"), "lookup_customer", "cust-0004").reason == "consent_withdrawn"


def test_handoff_keeps_purpose_and_cannot_widen(gw):
    p = P()
    child = gw.delegate(p, "agent-b")
    assert child.purpose == p.purpose and child.hops == 1
    with pytest.raises(PolicyDenied) as exc:
        gw.delegate(p, "agent-b", purpose="fraud_review")
    assert exc.value.reason == "purpose_cannot_change_in_handoff"
    assert gw.ledger.bodies()[-1]["decision"] == "deny"


def test_handoff_hop_limit(gw):
    p = P()
    for i in range(gw.max_hops):
        p = gw.delegate(p, f"agent-{i}")
    with pytest.raises(PolicyDenied) as exc:
        gw.delegate(p, "one-too-many")
    assert exc.value.reason == "max_hops_exceeded"


def test_memory_is_scoped_to_the_request(gw):
    a, b = P(rid="ra"), P(rid="rb")
    gw.remember(a, "k", "secret")
    assert gw.recall(a, "k").data == "secret"
    d = gw.recall(b, "k", from_request_id="ra")
    assert not d.allowed and d.reason == "cross_request_memory"


def test_sinks_redact_released_values_the_sink_may_not_hold(gw):
    p = P("fraud_review")
    info = gw.call(p, "lookup_customer", "cust-0005").data
    text = " | ".join(str(v) for v in info.values())
    out = gw.emit(p, "vendor_helpdesk", text, "cust-0005", approval="analyst")
    assert out.allowed and out.record["decision"] == "minimized"
    assert str(info["card_last4"]) not in out.data and "[REDACTED:financial]" in out.data
    assert str(info["loyalty_points"]) in out.data  # account class is allowed in that sink


def test_external_sink_needs_approval(gw):
    p = P("fraud_review")
    gw.call(p, "lookup_customer", "cust-0006")
    assert gw.emit(p, "vendor_helpdesk", "x", "cust-0006").reason == "approval_required"


def test_unknown_sink_denied(gw):
    assert gw.emit(P(), "nowhere", "hi").reason == "unknown_sink"


def test_ledger_never_stores_personal_values(gw):
    customers = make_customers(30)
    g = make_gateway(customers)
    p = P("fraud_review")
    g.call(p, "lookup_customer", "cust-0009")
    blob = json.dumps(g.ledger.entries)
    for value in customers["cust-0009"].values():
        assert str(value) not in blob


# ---------------------------------------------------------------- ledger
def build(gw, n=40):
    for i in range(n):
        gw.call(P(rid=f"q{i}"), "lookup_customer", f"cust-{i % 30:04d}")
    return gw.ledger.entries


def test_ledger_verifies_and_detects_edit(gw):
    entries = copy.deepcopy(build(gw))
    assert verify_entries(entries).ok
    entries[10]["body"]["decision"] = "deny"
    r = verify_entries(entries)
    assert not r.ok and r.index == 10


def test_ledger_detects_delete_and_reorder(gw):
    entries = build(gw)
    e = copy.deepcopy(entries)
    del e[5]
    assert not verify_entries(e).ok
    e = copy.deepcopy(entries)
    e[3], e[4] = e[4], e[3]
    assert not verify_entries(e).ok


def test_truncation_and_rewrite_need_an_anchor(gw):
    entries = copy.deepcopy(build(gw))
    head = entries[-1]["hash"]
    cut = entries[:-3]
    assert verify_entries(cut).ok  # chain alone cannot see this
    assert not verify_entries(cut, expected_head=head).ok
    # rewrite one entry and recompute the chain after it
    rew = copy.deepcopy(entries)
    rew[5]["body"]["decision"] = "deny"
    prev = rew[4]["hash"]
    for e in rew[5:]:
        e["prev"], e["hash"] = prev, entry_hash(e["body"], prev)
        prev = e["hash"]
    assert verify_entries(rew).ok
    assert not verify_entries(rew, expected_head=head).ok


def test_ledger_file_roundtrip_and_tamper(tmp_path):
    path = str(tmp_path / "l.jsonl")
    g = make_gateway(make_customers(5), ledger_path=path)
    g.call(P(), "lookup_customer", "cust-0001")
    g.call(P(), "lookup_customer", "cust-0002")
    again = Ledger(path)
    assert len(again.entries) == 2 and again.head == g.ledger.head
    text = open(path).read().replace('"minimized"', '"allow"', 1)
    open(path, "w").write(text)
    with pytest.raises(LedgerError):
        Ledger(path)


def test_invalid_record_is_refused(tmp_path):
    ledger = Ledger()
    bad = ActionRecord("r", "d", "a", "1", "p", "t", "read", [], "c", None, "internal", 0, "nope", "x")
    with pytest.raises(ValueError):
        ledger.append(bad)


# --------------------------------------------------------------- lineage
def test_trace_depth_counts_handoffs(gw):
    p = P()
    gw.call(p, "lookup_customer", "cust-0001")
    child = gw.delegate(p, "agent-b")
    gw.call(child, "lookup_customer", "cust-0001")
    depths = [n["depth"] for n in lineage.trace(gw.ledger.bodies(), "r1")]
    assert depths == [0, 0, 1]


def test_withdrawal_impact_lists_places_to_unwind(gw):
    p = P()
    gw.call(p, "lookup_customer", "cust-0001")
    gw.call(p, "update_points", "cust-0001", delta=1)  # denied, nothing released
    sref = subject_ref("cust-0001", gw.salt)
    hits = lineage.withdrawal_impact(gw.ledger.bodies(), sref)
    assert [h["tool"] for h in hits] == ["lookup_customer"]
    assert lineage.exposure_by_class(gw.ledger.bodies(), "r1") == {"account": 1, "identity": 1}


def test_dot_export_mentions_every_action(gw):
    p = P()
    gw.call(p, "lookup_customer", "cust-0001")
    dot = lineage.to_dot(gw.ledger.bodies(), "r1")
    assert dot.startswith("digraph") and "lookup_customer" in dot


# ---------------------------------------------------------------- ladder
def run_sandbox(gw, n):
    for i in range(n):
        gw.call(P(env="sandbox", rid=f"s{i}"), "lookup_customer", f"cust-{i % 30:04d}")


def test_ladder_blocks_until_enough_clean_actions(gw):
    run_sandbox(gw, 10)
    g = ladder.evaluate(gw.ledger.bodies(), "sandbox")
    assert not g.ready and any(c["name"] == "enough actions" and not c["passed"] for c in g.checks)
    run_sandbox(gw, 60)
    assert ladder.evaluate(gw.ledger.bodies(), "sandbox").ready


def test_ladder_shadow_needs_reviewer_agreement(gw):
    for i in range(120):
        gw.call(P(env="shadow", rid=f"h{i}"), "lookup_customer", f"cust-{i % 30:04d}")
    assert not ladder.evaluate(gw.ledger.bodies(), "shadow").ready
    assert not ladder.evaluate(gw.ledger.bodies(), "shadow", reviewer_agreement=0.8).ready
    assert ladder.evaluate(gw.ledger.bodies(), "shadow", reviewer_agreement=0.97).ready


def test_ladder_fails_on_broken_ledger(gw):
    run_sandbox(gw, 60)
    assert not ladder.evaluate(gw.ledger.bodies(), "sandbox", ledger_ok=False).ready


def test_ladder_limited_requires_full_approval_coverage(gw):
    for i in range(210):
        gw.call(P(env="limited", rid=f"l{i}"), "update_points", f"cust-{i % 30:04d}", approval="rep", delta=1)
    assert ladder.evaluate(gw.ledger.bodies(), "limited").ready
    # an allowed write with no approval recorded would lower coverage
    bodies = gw.ledger.bodies()
    bodies[-1] = {**bodies[-1], "approval": None}
    assert not ladder.evaluate(bodies, "limited").ready


# ------------------------------------------------------------- scorecard
def test_scorecard_roundtrip_and_score():
    ans = {"purpose": True, "minimization": False, "record": True, "approval": False, "sandbox": True}
    code = scorecard.encode(ans, "pilot", "engineer")
    assert code == "AAR1|pilot|10101|engineer"
    d = scorecard.decode(code)
    assert d["answers"] == ans and scorecard.score(d["answers"]) == 3


@pytest.mark.parametrize("bad", ["", "AAR2|pilot|10101|x", "AAR1|pilot|101|x", "AAR1|weird|10101|x", "AAR1|pilot|1010a|x"])
def test_scorecard_rejects_bad_codes(bad):
    with pytest.raises(ValueError):
        scorecard.decode(bad)


def test_scorecard_aggregate_suppresses_small_groups():
    codes = [scorecard.encode({"purpose": True}, "production", "x") for _ in range(6)]
    codes += [scorecard.encode({}, "none", "x") for _ in range(2)]
    agg = scorecard.aggregate(codes)
    assert agg["n"] == 8
    assert agg["by_status"]["production"]["mean_score"] == 1.0
    assert agg["by_status"]["none"]["mean_score"] == "suppressed"
    assert agg["pct_yes"]["purpose"] == 75.0


# ------------------------------------------------- repo consistency checks
ROOT = os.path.join(os.path.dirname(__file__), "..")


def test_schema_properties_match_dataclass_fields():
    import dataclasses
    schema = json.load(open(os.path.join(ROOT, "schema", "action-record.schema.json")))
    fields = {f.name for f in dataclasses.fields(ActionRecord)}
    assert set(schema["properties"]) == fields
    assert set(schema["required"]) <= fields


def test_record_dicts_have_only_schema_fields(gw):
    schema = json.load(open(os.path.join(ROOT, "schema", "action-record.schema.json")))
    gw.call(P(), "lookup_customer", "cust-0001")
    assert set(gw.ledger.bodies()[0]) == set(schema["properties"])


def test_scorecard_page_matches_python_instrument():
    html = open(os.path.join(ROOT, "..", "agent-privacy-clinic", "index.html"), encoding="utf-8").read()
    assert f'PREFIX = "{scorecard.PREFIX}"' in html
    for key in scorecard.KEYS:
        assert f'key: "{key}"' in html
    for status in scorecard.STATUSES:
        assert f'value="{status}"' in html


def test_example_responses_aggregate():
    codes = scorecard.read_codes(os.path.join(ROOT, "..", "agent-privacy-clinic", "responses_example.txt"))
    assert scorecard.aggregate(codes)["n"] == 60
