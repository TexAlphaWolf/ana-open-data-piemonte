"""Compare the NumPy indicators with the literal ones: on the real tables and on random ones."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from odpiemonte import indicators, reference
from odpiemonte.data import Dataset
from odpiemonte.load import MAX_AGE

RTOL = 1e-12


@dataclass
class Check:
    name: str
    units: int
    numbers: int  # values compared
    worst: float  # largest relative difference
    ok: bool


def compare(a: dict[str, npt.NDArray[np.float64]], b: dict[str, npt.NDArray[np.float64]]) -> tuple[int, float, bool]:
    """(values compared, largest relative difference, same). A `nan` must be `nan` in both."""
    n, worst, same = 0, 0.0, a.keys() == b.keys()
    for k in a:
        x, y = a[k], b.get(k)
        if y is None or x.shape != y.shape or (np.isnan(x) != np.isnan(y)).any():
            same = False
            continue
        ok = ~np.isnan(x)
        n += int(ok.sum()) + int((~ok).sum())
        if ok.any():
            den = np.maximum(np.abs(y[ok]), 1e-300)
            worst = max(worst, float(np.max(np.abs(x[ok] - y[ok]) / den)))
    return n, worst, same and worst <= RTOL


def random_counts(rng: np.random.Generator, units: int) -> npt.NDArray[np.int64]:
    """Random units, many of them awkward: empty classes, no children, no one over 60, one resident."""
    scale = rng.choice([0, 1, 3, 30, 1000], size=(units, 1, 1), p=[0.1, 0.3, 0.3, 0.2, 0.1])
    base = rng.integers(0, 4, size=(units, 2, MAX_AGE + 1)) * scale
    for i in range(units):
        kind = rng.integers(0, 6)
        if kind == 0:
            base[i, :, :15] = 0
        elif kind == 1:
            base[i, :, 60:] = 0
        elif kind == 2:
            base[i] = 0
            base[i, rng.integers(0, 2), rng.integers(0, MAX_AGE + 1)] = 1
    return np.asarray(base, dtype=np.int64)


def run(ds: Dataset | None, draws: int, seed: int) -> list[Check]:
    out: list[Check] = []
    tables = []
    if ds is not None:
        tables = [
            ("municipalities of Piemonte", ds.comuni.counts),
            ("provinces of Italy", ds.provinces.counts),
            ("regions of Italy", ds.regions.counts),
        ]
    rng = np.random.default_rng(seed)
    for i in range(draws):
        tables.append((f"random table {i + 1}", random_counts(rng, 40)))
    for name, counts in tables:
        n, worst, ok = compare(indicators.compute(counts), reference.compute(counts))
        out.append(Check(name, len(counts), n, worst, ok))
    return out
