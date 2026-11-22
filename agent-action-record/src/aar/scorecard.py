"""Agent Privacy Readiness Scorecard: scoring and anonymous aggregation.

Five yes/no checks. A respondent gets a short result code from the web page
in agent-privacy-clinic/index.html. This module decodes codes and summarizes them.
No personal data is collected. Groups smaller than MIN_CELL are suppressed.
"""
from __future__ import annotations

import csv
from collections import defaultdict
from typing import Dict, Iterable, List

QUESTIONS = [
    ("purpose", "Is the purpose of each request checked at the tool call?"),
    ("minimization", "Does each tool return only the fields that purpose needs?"),
    ("record", "Is a record written for every agent action, including denied ones?"),
    ("approval", "Does a person approve writes and sends that leave your boundary?"),
    ("sandbox", "Did the agent run on synthetic data before touching real data?"),
]
KEYS = [k for k, _ in QUESTIONS]
STATUSES = ("none", "pilot", "production")
MIN_CELL = 5
PREFIX = "AAR1"


def encode(answers: Dict[str, bool], status: str = "pilot", role: str = "other") -> str:
    bits = "".join("1" if answers.get(k) else "0" for k in KEYS)
    return f"{PREFIX}|{status}|{bits}|{role}"


def decode(code: str) -> dict:
    parts = code.strip().split("|")
    if len(parts) != 4 or parts[0] != PREFIX or len(parts[2]) != len(KEYS) or set(parts[2]) - {"0", "1"}:
        raise ValueError(f"bad result code: {code!r}")
    if parts[1] not in STATUSES:
        raise ValueError(f"bad status in code: {code!r}")
    return {"status": parts[1], "role": parts[3], "answers": {k: b == "1" for k, b in zip(KEYS, parts[2])}}


def score(answers: Dict[str, bool]) -> int:
    return sum(1 for k in KEYS if answers.get(k))


def read_codes(path: str) -> List[str]:
    with open(path, newline="", encoding="utf-8") as fh:
        if path.endswith(".csv"):
            rows = list(csv.reader(fh))
            return [r[0] for r in rows if r and r[0].startswith(PREFIX)]
        return [line.strip() for line in fh if line.strip().startswith(PREFIX)]


def aggregate(codes: Iterable[str]) -> dict:
    decoded = [decode(c) for c in codes]
    n = len(decoded)
    if n == 0:
        return {"n": 0}
    per_q = {k: sum(d["answers"][k] for d in decoded) / n for k in KEYS}
    scores = [score(d["answers"]) for d in decoded]
    by_status: Dict[str, List[int]] = defaultdict(list)
    for d, s in zip(decoded, scores):
        by_status[d["status"]].append(s)
    groups = {}
    for status, vals in by_status.items():
        groups[status] = {"n": len(vals), "mean_score": round(sum(vals) / len(vals), 2)} if len(vals) >= MIN_CELL else {"n": f"<{MIN_CELL}", "mean_score": "suppressed"}
    return {
        "n": n,
        "mean_score": round(sum(scores) / n, 2),
        "pct_yes": {k: round(v * 100, 1) for k, v in per_q.items()},
        "pct_scoring_zero_or_one": round(100 * sum(1 for s in scores if s <= 1) / n, 1),
        "by_status": groups,
    }
