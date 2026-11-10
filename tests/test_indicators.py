"""Hand-computed cases. Every case also goes through the literal implementation."""

from __future__ import annotations

import math

import numpy as np
import pytest

from odpiemonte import indicators, reference, verify
from odpiemonte.load import MAX_AGE

from .conftest import DRAWS, SEED, at, counts_of, flat


def both(*units: tuple[list[int], list[int]]) -> dict[str, np.ndarray]:
    counts = counts_of(*units)
    a, b = indicators.compute(counts), reference.compute(counts)
    n, worst, ok = verify.compare(a, b)
    assert ok, (worst, n)
    return a


def mix(**by_age: tuple[int, int]) -> tuple[list[int], list[int]]:
    """Residents at several ages: `a10=(males, females)`."""
    m, f = [0] * (MAX_AGE + 1), [0] * (MAX_AGE + 1)
    for key, (x, y) in by_age.items():
        m[int(key[1:])], f[int(key[1:])] = x, y
    return m, f


def test_hand_computed_unit() -> None:
    # 10 aged 5 (4 boys, 6 girls), 40 aged 30, 30 aged 62, 20 aged 70
    u = mix(a5=(4, 6), a30=(15, 25), a62=(10, 20), a70=(8, 12))
    x = both(u)
    assert x["population"][0] == 100
    assert (
        x["share_0_14"][0] == 10
        and x["share_15_64"][0] == 70
        and x["share_65_plus"][0] == 20
        and x["share_85_plus"][0] == 0
    )
    assert x["ageing_index"][0] == 200  # 20 old per 10 young, per 100
    assert x["dependency"][0] == pytest.approx(100 * 30 / 70)
    assert x["old_age_dependency"][0] == pytest.approx(100 * 20 / 70)
    assert math.isnan(x["turnover"][0])  # nobody aged 15 to 19
    assert x["working_age_structure"][0] == pytest.approx(100 * 30 / 40)  # aged 40-64 over aged 15-39
    assert x["sex_ratio"][0] == pytest.approx(100 * 37 / 63)
    assert x["mean_age"][0] == pytest.approx((10 * 5.5 + 40 * 30.5 + 30 * 62.5 + 20 * 70.5) / 100)


def test_median_is_interpolated_inside_the_age() -> None:
    # 100 residents: 30 aged 20, 40 aged 40, 30 aged 60. Half is 50: 30 below 40, so 40 + (50 - 30) / 40 = 40.5
    assert both(mix(a20=(15, 15), a40=(20, 20), a60=(15, 15)))["median_age"][0] == pytest.approx(40.5)
    # everyone aged 7: the median is inside age 7, halfway through the class
    assert both(at(7, 5, 5))["median_age"][0] == pytest.approx(7.5)
    # half exactly reached at the end of an age class: the first age at which half is reached
    assert both(mix(a10=(5, 5), a50=(5, 5)))["median_age"][0] == pytest.approx(10 + 1.0)


def test_ratios_without_a_denominator_are_nan_not_infinite() -> None:
    x = both(at(70, 3, 3), at(10, 2, 2), flat(1, 0, 0), (([0] * 101), ([0] * 101)))
    assert math.isnan(x["ageing_index"][0]) and not math.isnan(x["share_65_plus"][0])  # old people, no children
    assert x["ageing_index"][1] == 0 and math.isnan(x["old_age_dependency"][1])  # only children: nobody of working age
    assert math.isnan(x["sex_ratio"][2])  # no women
    assert all(math.isnan(x[k][3]) for k in x if k != "population") and x["population"][3] == 0  # an empty unit


def test_the_open_class_counts_at_the_top() -> None:
    x = both(mix(a100=(1, 1), a99=(1, 1)))
    assert x["share_85_plus"][0] == 100 and x["median_age"][0] == 100.0  # 99 + (2 - 0) / 2


def test_shares_add_up_and_the_two_implementations_agree_on_random_tables() -> None:
    rng = np.random.default_rng(SEED)
    for _ in range(DRAWS):
        counts = verify.random_counts(rng, 30)
        x = indicators.compute(counts)
        live = x["population"] > 0
        assert np.allclose((x["share_0_14"] + x["share_15_64"] + x["share_65_plus"])[live], 100)
        assert verify.compare(x, reference.compute(counts))[2]


def test_verify_can_fail() -> None:
    """A wrong second implementation must be reported, not waved through."""
    counts = counts_of(mix(a5=(1, 1), a70=(2, 2)))
    a = indicators.compute(counts)
    b = {k: v.copy() for k, v in a.items()}
    assert verify.compare(a, b)[2]
    b["ageing_index"] = b["ageing_index"] * (1 + 1e-6)
    assert not verify.compare(a, b)[2]
    c = {k: v.copy() for k, v in a.items()}
    c["turnover"] = np.array([1.0])  # a number where the other has nan
    assert not verify.compare(a, c)[2]
    d = dict(a)
    del d["mean_age"]
    assert not verify.compare(a, d)[2]


def test_run_on_random_tables_only() -> None:
    results = verify.run(None, 4, SEED)
    assert len(results) == 4 and all(r.ok for r in results) and all(r.units == 40 for r in results)
