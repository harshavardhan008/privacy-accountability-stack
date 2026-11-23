"""python -m clinic_exam [--customers 50] [--seed 2026] [--out results]"""
import argparse
import json
import os

from .report import to_markdown
from .runner import run_exam


def main():
    ap = argparse.ArgumentParser(description="Run the Clinic Exam on synthetic data.")
    ap.add_argument("--customers", type=int, default=50)
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--out", default=None, help="folder for exam.json and exam.md")
    a = ap.parse_args()
    res = run_exam(a.customers, a.seed)
    md = to_markdown(res)
    print(md)
    if a.out:
        os.makedirs(a.out, exist_ok=True)
        with open(os.path.join(a.out, "exam.json"), "w", encoding="utf-8") as fh:
            json.dump(res, fh, indent=2)
        with open(os.path.join(a.out, "exam.md"), "w", encoding="utf-8") as fh:
            fh.write(md)


if __name__ == "__main__":
    main()
