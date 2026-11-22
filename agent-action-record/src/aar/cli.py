"""Command line: aar verify | trace | dot | graduate | score"""
from __future__ import annotations

import argparse
import json
import sys

from . import ladder, lineage, scorecard
from .ledger import load_entries, verify_entries


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="aar", description="Agent Action Record tools")
    sub = ap.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("verify", help="verify a ledger hash chain")
    v.add_argument("ledger")
    v.add_argument("--head", help="externally anchored head hash")

    t = sub.add_parser("trace", help="show the actions of one request")
    t.add_argument("ledger")
    t.add_argument("request_id")

    d = sub.add_parser("dot", help="export a request as Graphviz DOT")
    d.add_argument("ledger")
    d.add_argument("request_id")

    g = sub.add_parser("graduate", help="check readiness to move up a rung")
    g.add_argument("ledger")
    g.add_argument("--rung", required=True, choices=ladder.RUNGS[:-1])
    g.add_argument("--reviewer-agreement", type=float)

    s = sub.add_parser("score", help="summarize scorecard result codes")
    s.add_argument("codes", help="text or csv file of result codes")

    args = ap.parse_args(argv)
    if args.cmd == "score":
        print(json.dumps(scorecard.aggregate(scorecard.read_codes(args.codes)), indent=2))
        return 0

    entries = load_entries(args.ledger)
    result = verify_entries(entries, getattr(args, "head", None))
    bodies = [e["body"] for e in entries]
    if args.cmd == "verify":
        print(f"{'OK' if result.ok else 'FAILED'}: {result.message} (entries={len(entries)}, head={result.head})")
        return 0 if result.ok else 1
    if args.cmd == "trace":
        for n in lineage.trace(bodies, args.request_id):
            print(f'{"  " * n["depth"]}{n["tool"]:<28} {n["decision"]:<9} {",".join(n["data_classes"]) or "-":<28} {n["reason"]}')
        return 0
    if args.cmd == "dot":
        print(lineage.to_dot(bodies, args.request_id))
        return 0
    if args.cmd == "graduate":
        grad = ladder.evaluate(bodies, args.rung, ledger_ok=result.ok, reviewer_agreement=args.reviewer_agreement)
        for c in grad.checks:
            print(f'[{"PASS" if c["passed"] else "FAIL"}] {c["name"]}: {c["detail"]}')
        print(f'Ready to move {grad.current} -> {grad.next}: {"YES" if grad.ready else "NO"}')
        return 0 if grad.ready else 2
    return 1


if __name__ == "__main__":
    sys.exit(main())
