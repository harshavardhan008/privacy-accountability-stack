"""Small statistics helpers. Standard library only."""
from __future__ import annotations

from math import sqrt
from typing import Tuple


def wilson(successes: int, n: int, z: float = 1.96) -> Tuple[float, float]:
    """Wilson score interval for a proportion. Better than the normal
    approximation when n is small or the rate is near 0 or 1."""
    if n <= 0:
        return (0.0, 1.0)
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def rate(successes: int, n: int) -> dict:
    lo, hi = wilson(successes, n)
    return {"k": successes, "n": n, "rate": (successes / n) if n else 0.0, "lo": lo, "hi": hi}
