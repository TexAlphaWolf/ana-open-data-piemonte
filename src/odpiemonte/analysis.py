"""The analysis of Piemonte: indicators, provinces against Italy, municipalities by size, concentration and extremes."""

from __future__ import annotations

from typing import Any

import numpy as np
import numpy.typing as npt

from odpiemonte import indicators
from odpiemonte.data import PIEMONTE_PROVINCES, PIEMONTE_REGION, Dataset
from odpiemonte.load import DataError

SIZE_CLASSES = [(0, 500), (500, 1000), (1000, 5000), (5000, 20000), (20000, None)]
MIN_POPULATION = 1000  # below it an index made of a few dozen people says more about luck than about the place
TOP = 5


def label(lo: int, hi: int | None) -> str:
    if hi is None:
        return f"{lo:,} and over"
    if lo == 0:
        return f"under {hi:,}"
    return f"{lo:,} to {hi - 1:,}"


def number(x: float) -> float | None:
    """A float for JSON: null when it is not a number."""
    return None if np.isnan(x) else float(x)


def row(ix: dict[str, npt.NDArray[np.float64]], i: int) -> dict[str, float | None]:
    return {k: number(v[i]) for k, v in ix.items()}


def gini(values: npt.NDArray[np.float64]) -> float:
    """Gini coefficient of non-negative values: 0 when all are equal, near 1 when one has everything."""
    x = np.sort(values)
    n = len(x)
    return float(2 * np.sum(np.arange(1, n + 1) * x) / (n * x.sum()) - (n + 1) / n)


def rank_desc(values: npt.NDArray[np.float64]) -> npt.NDArray[np.int64]:
    """1 for the largest value."""
    order = np.argsort(-values, kind="stable")
    ranks = np.empty(len(values), dtype=np.int64)
    ranks[order] = np.arange(1, len(values) + 1)
    return ranks


def pyramid(counts: npt.NDArray[np.int64]) -> dict[str, list[int]]:
    both = counts.sum(axis=0)
    return {"males": [int(x) for x in both[0]], "females": [int(x) for x in both[1]]}


def build_report(ds: Dataset, source: str = "ISTAT POSAS") -> dict[str, Any]:
    pm = ds.comuni
    ix = indicators.compute(pm.counts)
    pop = ix["population"]
    total = pm.counts.sum(axis=0, keepdims=True)
    pie = indicators.compute(total)

    # Provinces of Piemonte against every province of Italy
    all_prov = indicators.compute(ds.provinces.counts)
    rank_age = rank_desc(np.nan_to_num(all_prov["ageing_index"], nan=-1.0))
    provinces = []
    for code in PIEMONTE_PROVINCES:
        i = ds.provinces.index(code)
        mine = pm.with_prefix(code)
        provinces.append(
            {
                "code": code,
                "name": ds.provinces.names[i],
                "comuni": len(mine),
                "indicators": row(all_prov, i),
                "ageing_rank_of_107": int(rank_age[i]),
            }
        )

    # Regions
    reg = indicators.compute(ds.regions.counts)
    rank_reg = rank_desc(reg["ageing_index"])
    italy = indicators.compute(ds.regions.counts.sum(axis=0, keepdims=True))
    regions = [
        {
            "code": ds.regions.codes[i],
            "name": ds.regions.names[i],
            "indicators": row(reg, i),
            "ageing_rank_of_20": int(rank_reg[i]),
        }
        for i in np.argsort(rank_reg)
    ]

    # Municipalities by size
    sizes = []
    for lo, hi in SIZE_CLASSES:
        m = (pop >= lo) & ((pop < hi) if hi is not None else np.ones(len(pop), dtype=bool))
        agg = indicators.compute(pm.counts[m].sum(axis=0, keepdims=True))
        idx = ix["ageing_index"][m]
        idx = idx[~np.isnan(idx)]
        sizes.append(
            {
                "label": label(lo, hi),
                "comuni": int(m.sum()),
                "population": int(pop[m].sum()),
                "share_of_population": 100 * float(pop[m].sum()) / float(pop.sum()),
                "pooled": row(agg, 0),
                "ageing_index_p10": float(np.percentile(idx, 10)),
                "ageing_index_p90": float(np.percentile(idx, 90)),
            }
        )

    order = np.argsort(-pop, kind="stable")
    big = pop >= MIN_POPULATION
    key = np.where(big & ~np.isnan(ix["ageing_index"]), ix["ageing_index"], np.nan)
    oldest = [i for i in np.argsort(-np.nan_to_num(key, nan=-1.0), kind="stable")[:TOP]]
    youngest = [i for i in np.argsort(np.nan_to_num(key, nan=np.inf), kind="stable")[:TOP]]

    def pick(i: int) -> dict[str, Any]:
        return {
            "code": pm.codes[i],
            "name": pm.names[i],
            "population": int(pop[i]),
            "ageing_index": number(ix["ageing_index"][i]),
            "median_age": number(ix["median_age"][i]),
        }

    by_age = pm.counts.sum(axis=(0, 1))
    report: dict[str, Any] = {
        "kind": "report",
        "source": source,
        "year": pm.year,
        "estimate": pm.estimate,
        "files": ds.files,
        "piemonte": {
            "comuni": len(pm),
            "population": pm.total(),
            "indicators": row(pie, 0),
            "italy": row(italy, 0),
            "ageing_rank_of_20": int(rank_reg[ds.regions.index(PIEMONTE_REGION)]),
            "pyramid": pyramid(pm.counts),
            "italy_pyramid": pyramid(ds.regions.counts),
            "largest_age": int(np.argmax(by_age)),
            "largest_age_residents": int(np.max(by_age)),
            "age_0_residents": int(by_age[0]),
        },
        "provinces": provinces,
        "regions": regions,
        "sizes": sizes,
        "concentration": {
            "largest": pick(int(order[0])),
            "largest_share": 100 * float(pop[order[0]]) / float(pop.sum()),
            "top10_share": 100 * float(pop[order[:10]].sum()) / float(pop.sum()),
            "gini": gini(pop),
            "median_comune_population": float(np.median(pop)),
            "under_1000": int((pop < 1000).sum()),
            "under_1000_population_share": 100 * float(pop[pop < 1000].sum()) / float(pop.sum()),
        },
        "extremes": {
            "min_population": MIN_POPULATION,
            "oldest": [pick(int(i)) for i in oldest],
            "youngest": [pick(int(i)) for i in youngest],
            "no_children": [pick(int(i)) for i in np.where(np.isnan(ix["ageing_index"]))[0]],
            "share_65_plus_at_least_40": int((ix["share_65_plus"] >= 40).sum()),
            "share_65_plus_at_least_30": int((ix["share_65_plus"] >= 30).sum()),
        },
        "reconciliation": reconcile(ds),
    }
    return report


def reconcile(ds: Dataset) -> dict[str, Any]:
    """The three files describe the same people at three levels, so their totals must agree."""
    out: dict[str, Any] = {"provinces": [], "region": {}, "italy": {}}
    for code in PIEMONTE_PROVINCES:
        mine = ds.comuni.with_prefix(code).total()
        theirs = int(ds.provinces.counts[ds.provinces.index(code)].sum())
        out["provinces"].append({"code": code, "comuni_total": mine, "province_total": theirs, "equal": mine == theirs})
    mine = ds.comuni.total()
    reg = int(ds.regions.counts[ds.regions.index(PIEMONTE_REGION)].sum())
    out["region"] = {"comuni_total": mine, "region_total": reg, "equal": mine == reg}
    a, b = ds.provinces.total(), ds.regions.total()
    out["italy"] = {"provinces_total": a, "regions_total": b, "equal": a == b}
    ages_equal = bool((ds.provinces.counts.sum(axis=0) == ds.regions.counts.sum(axis=0)).all())
    out["italy"]["equal_by_age_and_sex"] = ages_equal
    out["all_equal"] = bool(
        all(p["equal"] for p in out["provinces"]) and out["region"]["equal"] and out["italy"]["equal"] and ages_equal
    )
    if not out["all_equal"]:
        raise DataError("the municipalities, provinces and regions do not add up to the same population")
    return out
