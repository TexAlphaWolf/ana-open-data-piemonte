"""The ISTAT demographic indicators, for many units at once (NumPy). `reference.py` computes the same by plain loops.

Ages are completed years: the class `a` covers `[a, a + 1)`, and `100` stands for "100 and over". A ratio whose denominator
is zero is `nan` (reported as null): a municipality with no child under 15 has no ageing index, not an infinite one."""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

from odpiemonte.load import MAX_AGE

# (name, what it is). The ratios are per 100, as ISTAT publishes them.
INDICATORS: dict[str, str] = {
    "population": "residents on 1 January",
    "share_0_14": "% aged 0 to 14",
    "share_15_64": "% aged 15 to 64",
    "share_65_plus": "% aged 65 and over",
    "share_85_plus": "% aged 85 and over",
    "ageing_index": "aged 65+ per 100 aged 0-14 (indice di vecchiaia)",
    "dependency": "(0-14 plus 65+) per 100 aged 15-64 (indice di dipendenza strutturale)",
    "old_age_dependency": "65+ per 100 aged 15-64 (indice di dipendenza degli anziani)",
    "turnover": "aged 60-64 per 100 aged 15-19 (indice di ricambio della popolazione attiva)",
    "working_age_structure": "aged 40-64 per 100 aged 15-39 (indice di struttura della popolazione attiva)",
    "sex_ratio": "males per 100 females",
    "median_age": "median age, interpolated inside the single year of age",
    "mean_age": "mean age, each class counted at its middle",
}
NAN = float("nan")


def band(by_age: npt.NDArray[np.int64], lo: int, hi: int) -> npt.NDArray[np.int64]:
    """Residents aged lo to hi included, for every unit. `by_age` is `(units, ages)`."""
    return np.asarray(by_age[:, lo : hi + 1].sum(axis=1), dtype=np.int64)


def ratio(num: npt.NDArray[np.int64], den: npt.NDArray[np.int64], scale: float = 100.0) -> npt.NDArray[np.float64]:
    out = np.full(num.shape, NAN)
    ok = den > 0
    out[ok] = scale * num[ok] / den[ok]
    return out


def median_age(by_age: npt.NDArray[np.int64]) -> npt.NDArray[np.float64]:
    """The age below which half of the residents are, taken as `a + (n/2 - residents below a) / residents of age a`."""
    cum = np.cumsum(by_age, axis=1)
    n = cum[:, -1]
    half = n / 2
    out = np.full(len(by_age), NAN)
    for i in range(len(by_age)):
        if n[i] == 0:
            continue
        a = int(np.searchsorted(cum[i], half[i], side="left"))
        below = cum[i, a - 1] if a > 0 else 0
        out[i] = a + (half[i] - below) / by_age[i, a]
    return out


def compute(counts: npt.NDArray[np.int64]) -> dict[str, npt.NDArray[np.float64]]:
    """The indicators of every unit of `counts[unit, sex, age]`."""
    by_age = counts.sum(axis=1)
    pop = by_age.sum(axis=1)
    young, work, old, very_old = (
        band(by_age, 0, 14),
        band(by_age, 15, 64),
        band(by_age, 65, MAX_AGE),
        band(by_age, 85, MAX_AGE),
    )
    ages = np.arange(MAX_AGE + 1) + 0.5
    mean = np.full(len(pop), NAN)
    ok = pop > 0
    mean[ok] = (by_age[ok] * ages).sum(axis=1) / pop[ok]
    return {
        "population": pop.astype(np.float64),
        "share_0_14": ratio(young, pop),
        "share_15_64": ratio(work, pop),
        "share_65_plus": ratio(old, pop),
        "share_85_plus": ratio(very_old, pop),
        "ageing_index": ratio(old, young),
        "dependency": ratio(young + old, work),
        "old_age_dependency": ratio(old, work),
        "turnover": ratio(band(by_age, 60, 64), band(by_age, 15, 19)),
        "working_age_structure": ratio(band(by_age, 40, 64), band(by_age, 15, 39)),
        "sex_ratio": ratio(counts[:, 0].sum(axis=1), counts[:, 1].sum(axis=1)),
        "median_age": median_age(by_age),
        "mean_age": mean,
    }
