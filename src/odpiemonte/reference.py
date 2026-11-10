"""The same indicators as `indicators.py`, written as literally as possible: one unit at a time, one age at a time, plain
Python numbers. It is slower and it is meant to be obviously right; `odp verify` compares the two."""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

from odpiemonte.indicators import INDICATORS, NAN
from odpiemonte.load import MAX_AGE


def _per_100(num: int, den: int) -> float:
    return 100.0 * num / den if den > 0 else NAN


def unit(males: list[int], females: list[int]) -> dict[str, float]:
    """The indicators of one unit, from its males and females by age (0 to 100)."""
    both = [m + f for m, f in zip(males, females, strict=True)]
    n = sum(both)

    def between(lo: int, hi: int) -> int:
        return sum(both[a] for a in range(lo, hi + 1))

    young, work, old = between(0, 14), between(15, 64), between(65, MAX_AGE)
    median = NAN
    if n > 0:
        below = 0
        for a in range(MAX_AGE + 1):  # the first age at which half of the residents are reached
            if below + both[a] >= n / 2:
                median = a + (n / 2 - below) / both[a]
                break
            below += both[a]
    return {
        "population": float(n),
        "share_0_14": _per_100(young, n),
        "share_15_64": _per_100(work, n),
        "share_65_plus": _per_100(old, n),
        "share_85_plus": _per_100(between(85, MAX_AGE), n),
        "ageing_index": _per_100(old, young),
        "dependency": _per_100(young + old, work),
        "old_age_dependency": _per_100(old, work),
        "turnover": _per_100(between(60, 64), between(15, 19)),
        "working_age_structure": _per_100(between(40, 64), between(15, 39)),
        "sex_ratio": _per_100(sum(males), sum(females)),
        "median_age": median,
        "mean_age": sum((a + 0.5) * both[a] for a in range(MAX_AGE + 1)) / n if n > 0 else NAN,
    }


def compute(counts: npt.NDArray[np.int64]) -> dict[str, npt.NDArray[np.float64]]:
    rows = [unit([int(x) for x in c[0]], [int(x) for x in c[1]]) for c in counts]
    return {k: np.array([r[k] for r in rows], dtype=np.float64) for k in INDICATORS}
