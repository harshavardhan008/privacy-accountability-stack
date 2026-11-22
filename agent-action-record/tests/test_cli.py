import json

from aar.cli import main
from aar.ledger import Ledger
from aar import PurposePass
from examples.shared import make_customers, make_gateway


def make_file(tmp_path):
    path = str(tmp_path / "l.jsonl")
    g = make_gateway(make_customers(10), ledger_path=path)
    g.call(PurposePass("r1", "rep", "loyalty_support", "agent"), "lookup_customer", "cust-0001")
    return path, g.ledger.head


def test_verify_ok_and_head_mismatch(tmp_path, capsys):
    path, head = make_file(tmp_path)
    assert main(["verify", path]) == 0
    assert main(["verify", path, "--head", head]) == 0
    assert main(["verify", path, "--head", "0" * 64]) == 1


def test_trace_and_dot(tmp_path, capsys):
    path, _ = make_file(tmp_path)
    assert main(["trace", path, "r1"]) == 0
    assert "lookup_customer" in capsys.readouterr().out
    assert main(["dot", path, "r1"]) == 0
    assert "digraph" in capsys.readouterr().out


def test_graduate_reports_not_ready(tmp_path, capsys):
    path, _ = make_file(tmp_path)
    assert main(["graduate", path, "--rung", "sandbox"]) == 2
    assert "NO" in capsys.readouterr().out


def test_score_command(tmp_path, capsys):
    f = tmp_path / "codes.txt"
    f.write_text("AAR1|pilot|11111|eng\nAAR1|pilot|00000|eng\n")
    assert main(["score", str(f)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["n"] == 2 and out["mean_score"] == 2.5
