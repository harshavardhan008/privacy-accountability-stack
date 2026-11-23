"""Entry point for the browser page."""
import json

from .report import to_markdown
from .runner import run_exam


def run(customers, seed="2026"):
    res = run_exam(int(customers), int(seed))
    return json.dumps({"res": res, "md": to_markdown(res)})
