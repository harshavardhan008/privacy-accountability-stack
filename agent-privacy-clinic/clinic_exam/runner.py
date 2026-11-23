"""Run every probe against both targets over many synthetic customers."""
from __future__ import annotations

import copy
from collections import defaultdict
from typing import Dict, List

try:
    from examples.shared import make_customers
except ImportError:
    from demo_shared import make_customers

from .probes import LEAKS, PROBES
from .stats import rate
from .targets import GuardedTarget, LayeredTarget, ScannerTarget, UnguardedTarget

WHO = ("unguarded", "scanner", "guarded", "layered")
TARGETS = (UnguardedTarget, ScannerTarget, GuardedTarget, LayeredTarget)


def run_exam(n_customers: int = 50, seed: int = 2026) -> dict:
    base = make_customers(n_customers, seed)
    sids = sorted(base)
    per_probe: Dict[str, Dict[str, List[int]]] = {p.id: {w: [0, 0] for w in WHO} for p in PROBES}
    rec = {w: {"attempts": 0, "records": 0, "chains_ok": 0, "chains": 0} for w in ("guarded", "layered")}

    for i, sid in enumerate(sids):
        for p in PROBES:
            for tcls in TARGETS:
                customers = copy.deepcopy(base)  # fresh state per trial
                t = tcls(customers)
                ok = bool(p.run(t, base[sid], sid, f"{i}-{p.id}"))
                per_probe[p.id][t.name][0] += 1 if ok else 0
                per_probe[p.id][t.name][1] += 1
                if t.name in ("guarded", "layered"):
                    st = t.record_stats()
                    rr = rec[t.name]
                    rr["attempts"] += st["attempts"]
                    rr["records"] += st["records"]
                    rr["chains"] += 1
                    rr["chains_ok"] += 1 if st["chain_ok"] else 0

    def agg(kind, leak=None):
        out = {}
        for who in WHO:
            k = n = 0
            for p in PROBES:
                if p.kind != kind or (leak and p.leak != leak):
                    continue
                k += per_probe[p.id][who][0]
                n += per_probe[p.id][who][1]
            out[who] = rate(k, n)
        return out

    by_leak = {}
    for key, label in LEAKS.items():
        if any(p.kind == "attack" and p.leak == key for p in PROBES):
            by_leak[key] = {"label": label, **agg("attack", key)}

    benign = agg("benign")
    return {
        "customers": n_customers,
        "seed": seed,
        "trials_per_target": len(sids) * len(PROBES),
        "attack": agg("attack"),
        "by_leak": by_leak,
        "benign_success": benign,
        "known_limits": agg("known_limit"),
        "records": {w: {**v, "completeness": (v["records"] / v["attempts"]) if v["attempts"] else 0.0} for w, v in rec.items()},
        "probes": [{"id": p.id, "title": p.title, "leak": p.leak, "kind": p.kind,
                    **{w: rate(*per_probe[p.id][w]) for w in WHO}} for p in PROBES],
    }
