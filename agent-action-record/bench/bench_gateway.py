"""Gateway overhead only. Run:  python bench/bench_gateway.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from evaluate import N, overhead  # noqa: E402
from examples.shared import make_customers  # noqa: E402

if __name__ == "__main__":
    print(overhead(make_customers(N)))
