import json

from clinic_exam.report import to_markdown
from clinic_exam.runner import run_exam
from clinic_exam.stats import wilson


def test_wilson_known_values():
    lo, hi = wilson(0, 10)
    assert lo == 0.0 and abs(hi - 0.2775) < 0.001
    lo, hi = wilson(5, 10)
    assert abs(lo - 0.2366) < 0.001 and abs(hi - 0.7634) < 0.001
    assert wilson(0, 0) == (0.0, 1.0)


RES = run_exam(8, seed=7)


def probe(pid):
    return next(p for p in RES["probes"] if p["id"] == pid)


def test_structural_attacks_stopped_by_gateway():
    for p in RES["probes"]:
        if p["kind"] == "attack":
            assert p["unguarded"]["rate"] == 1.0, p["id"]
            assert p["guarded"]["rate"] == 0.0, p["id"]
            assert p["layered"]["rate"] == 0.0, p["id"]


def test_legitimate_work_still_works():
    for p in RES["probes"]:
        if p["kind"] == "benign":
            for who in ("unguarded", "scanner", "guarded", "layered"):
                assert p[who]["rate"] == 1.0, (p["id"], who)


def test_known_limits_are_reported_not_hidden():
    for pid in ("K1", "K2", "K3", "K4", "K5"):
        assert probe(pid)["guarded"]["rate"] == 1.0, pid
    k6 = probe("K6")
    assert k6["guarded"]["rate"] == 1.0
    assert k6["scanner"]["rate"] == 0.0
    assert k6["layered"]["rate"] == 0.0


def test_every_gateway_action_leaves_a_record():
    for who in ("guarded", "layered"):
        r = RES["records"][who]
        assert r["records"] == r["attempts"] > 0
        assert r["chains_ok"] == r["chains"]


def test_deterministic_and_report_renders():
    again = run_exam(8, seed=7)
    assert json.dumps(again, sort_keys=True) == json.dumps(RES, sort_keys=True)
    md = to_markdown(RES)
    assert "Known limits" in md and "—" not in md
