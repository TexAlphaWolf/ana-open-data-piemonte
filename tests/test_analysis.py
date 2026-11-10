from __future__ import annotations

import numpy as np
import pytest

from odpiemonte import analysis
from odpiemonte.data import load_dataset

from .conftest import DATA

DS = load_dataset(DATA)
REP = analysis.build_report(DS)


def test_gini_ranks_and_labels() -> None:
    assert analysis.gini(np.array([5.0, 5.0, 5.0, 5.0])) == pytest.approx(0)
    assert analysis.gini(np.array([0.0, 0.0, 0.0, 10.0])) == pytest.approx(0.75)  # (n - 1) / n
    assert analysis.gini(np.array([1.0, 2.0, 3.0])) == pytest.approx(2 * (1 + 4 + 9) / (3 * 6) - 4 / 3)
    assert list(analysis.rank_desc(np.array([3.0, 9.0, 1.0, 9.0]))) == [3, 1, 4, 2]  # ties by position
    assert (
        analysis.label(0, 500) == "under 500"
        and analysis.label(500, 1000) == "500 to 999"
        and analysis.label(20000, None) == "20,000 and over"
    )
    assert analysis.number(float("nan")) is None and analysis.number(2.5) == 2.5


def test_the_size_classes_partition_the_municipalities() -> None:
    sizes = REP["sizes"]
    assert sum(s["comuni"] for s in sizes) == 1180 and sum(s["population"] for s in sizes) == 4_255_006
    assert sum(s["share_of_population"] for s in sizes) == pytest.approx(100)
    assert [s["label"] for s in sizes] == [
        "under 500",
        "500 to 999",
        "1,000 to 4,999",
        "5,000 to 19,999",
        "20,000 and over",
    ]


def test_the_report_is_consistent_with_itself() -> None:
    p = REP["piemonte"]
    assert p["comuni"] == 1180 and p["population"] == 4_255_006 and p["indicators"]["population"] == 4_255_006
    assert sum(r["indicators"]["population"] for r in REP["provinces"]) == p["population"]
    assert sum(r["comuni"] for r in REP["provinces"]) == 1180
    assert sum(p["pyramid"]["males"]) + sum(p["pyramid"]["females"]) == p["population"]
    assert [r["ageing_rank_of_20"] for r in REP["regions"]] == list(range(1, 21))
    ages = [r["indicators"]["ageing_index"] for r in REP["regions"]]
    assert ages == sorted(ages, reverse=True)
    names = {r["name"]: r["ageing_rank_of_20"] for r in REP["regions"]}
    assert names["Piemonte"] == p["ageing_rank_of_20"]
    assert all(1 <= r["ageing_rank_of_107"] <= 107 for r in REP["provinces"])


def test_extremes_respect_the_minimum_population() -> None:
    e = REP["extremes"]
    assert all(x["population"] >= e["min_population"] for x in e["oldest"] + e["youngest"])
    old = [x["ageing_index"] for x in e["oldest"]]
    young = [x["ageing_index"] for x in e["youngest"]]
    assert old == sorted(old, reverse=True) and young == sorted(young) and min(old) > max(young)
    assert all(x["ageing_index"] is None for x in e["no_children"])


def test_the_report_has_no_nan() -> None:
    import json

    assert "NaN" not in json.dumps(REP, allow_nan=True)
    json.dumps(REP, allow_nan=False)
