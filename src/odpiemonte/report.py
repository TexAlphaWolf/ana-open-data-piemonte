"""Markdown and figures from a `report.json` or a `bench.json`. The Markdown is a pure function of the JSON."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from odpiemonte.indicators import INDICATORS

COLORS = {"main": "#0072b2", "italy": "#666666", "accent": "#d55e00", "second": "#009e73"}


def f1(x: float | None) -> str:
    return "-" if x is None else f"{x:,.1f}"


def f0(x: float | None) -> str:
    return "-" if x is None else f"{x:,.0f}"


def fmt_s(s: float) -> str:
    if s < 1e-3:
        return f"{s * 1e6:,.0f} us"
    if s < 1:
        return f"{s * 1e3:,.1f} ms"
    return f"{s:,.2f} s"


def render_report(rep: dict[str, Any]) -> str:
    p, c, e = rep["piemonte"], rep["concentration"], rep["extremes"]
    pi, it = p["indicators"], p["italy"]
    est = " (an estimate)" if rep["estimate"] else ""
    no_children = ", ".join(f"{x['name']} ({x['population']} residents)" for x in e["no_children"]) or "none"
    out = [
        "# Piemonte report",
        "",
        f"Source: {rep['source']}, resident population by age and sex on 1 January {rep['year']}{est}. "
        f"{p['comuni']:,} municipalities, {p['population']:,} residents.",
        "",
        "## 1. Piemonte against Italy",
        "",
        "| Indicator | Piemonte | Italy |",
        "|---|---|---|",
    ]
    for k, what in INDICATORS.items():
        if k == "population":
            continue
        out.append(f"| {k} ({what}) | {f1(pi[k])} | {f1(it[k])} |")
    out += [
        "",
        f"Piemonte is the {p['ageing_rank_of_20']}th oldest of the 20 regions by ageing index.",
        "",
        "## 2. Provinces",
        "",
        "| Province | Municipalities | Residents | Median age | 65+ % | Ageing index | Rank of 107 (1 = oldest) |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in sorted(rep["provinces"], key=lambda r: -r["indicators"]["ageing_index"]):
        i = r["indicators"]
        out.append(
            f"| {r['name']} | {r['comuni']:,} | {f0(i['population'])} | {f1(i['median_age'])} | {f1(i['share_65_plus'])} | {f1(i['ageing_index'])} | {r['ageing_rank_of_107']} |"
        )
    out += [
        "",
        "## 3. Regions",
        "",
        "| Region | Residents | Median age | 65+ % | Ageing index | Rank of 20 |",
        "|---|---|---|---|---|---|",
    ]
    for r in rep["regions"]:
        i = r["indicators"]
        out.append(
            f"| {r['name']} | {f0(i['population'])} | {f1(i['median_age'])} | {f1(i['share_65_plus'])} | {f1(i['ageing_index'])} | {r['ageing_rank_of_20']} |"
        )
    out += [
        "",
        "## 4. Municipalities by size",
        "",
        "| Residents | Municipalities | Population | % of Piemonte | Median age (pooled) | 65+ % (pooled) | Ageing index (pooled) | Ageing index, 10th to 90th percentile of municipalities |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for s in rep["sizes"]:
        pl = s["pooled"]
        out.append(
            f"| {s['label']} | {s['comuni']:,} | {s['population']:,} | {f1(s['share_of_population'])} | {f1(pl['median_age'])} | {f1(pl['share_65_plus'])} | {f1(pl['ageing_index'])} | {f0(s['ageing_index_p10'])} to {f0(s['ageing_index_p90'])} |"
        )
    out += [
        "",
        "## 5. Concentration and extremes",
        "",
        f"- Largest municipality: {c['largest']['name']}, {c['largest']['population']:,} residents, {f1(c['largest_share'])}% of Piemonte; the ten largest hold {f1(c['top10_share'])}%.",
        f"- Gini coefficient of municipality sizes: {c['gini']:.3f}. Median municipality: {f0(c['median_comune_population'])} residents.",
        f"- {c['under_1000']:,} municipalities have fewer than 1,000 residents and hold {f1(c['under_1000_population_share'])}% of the population.",
        f"- {e['share_65_plus_at_least_40']} municipalities have 40% or more aged 65+; {e['share_65_plus_at_least_30']} have 30% or more.",
        f"- With no child aged 0 to 14 (no ageing index): {no_children}.",
        "",
        f"Oldest and youngest by ageing index, among municipalities with at least {e['min_population']:,} residents:",
        "",
        "| | Municipality | Residents | Ageing index | Median age |",
        "|---|---|---|---|---|",
    ]
    for tag, rows in (("oldest", e["oldest"]), ("youngest", e["youngest"])):
        for r in rows:
            out.append(
                f"| {tag} | {r['name']} | {r['population']:,} | {f1(r['ageing_index'])} | {f1(r['median_age'])} |"
            )
    r = rep["reconciliation"]
    out += [
        "",
        "## 6. The three files agree",
        "",
        "The municipalities of each province add up to the province row ("
        + ", ".join(f"{x['code']}: {x['comuni_total']:,}" for x in r["provinces"])
        + f"), the municipalities of Piemonte to the region row ({r['region']['comuni_total']:,}), and the 107 provinces to the 20 regions "
        f"({r['italy']['provinces_total']:,} residents, equal for every age and sex).",
        "",
    ]
    return "\n".join(out)


def report_figure(rep: dict[str, Any], path: Path) -> None:
    fig, ax = plt.subplots(1, 3, figsize=(19.5, 6), constrained_layout=True)
    p = rep["piemonte"]
    ages = np.arange(len(p["pyramid"]["males"]))
    for who, pyr, col in (("Piemonte", p["pyramid"], COLORS["main"]), ("Italy", p["italy_pyramid"], COLORS["italy"])):
        both = np.array(pyr["males"]) + np.array(pyr["females"])
        ax[0].plot(ages, 100 * both / both.sum(), label=who, color=col, lw=2)
    ax[0].set(title="Share of residents by age", xlabel="age (100 = 100 and over)", ylabel="% of residents")
    ax[0].legend(frameon=False)
    names = [r["name"] for r in rep["provinces"]] + ["Piemonte", "Italy"]
    vals = [r["indicators"]["ageing_index"] for r in rep["provinces"]] + [
        p["indicators"]["ageing_index"],
        p["italy"]["ageing_index"],
    ]
    order = np.argsort(vals)
    cols = [
        COLORS["main"]
        if i < len(rep["provinces"])
        else (COLORS["accent"] if names[i] == "Piemonte" else COLORS["italy"])
        for i in order
    ]
    ax[1].barh([names[i] for i in order], [vals[i] for i in order], color=cols)
    ax[1].set(title="Ageing index (65+ per 100 aged 0-14)", xlabel="per 100")
    sizes = rep["sizes"]
    ax[2].bar([s["label"] for s in sizes], [s["pooled"]["ageing_index"] for s in sizes], color=COLORS["second"])
    for i, s in enumerate(sizes):
        ax[2].plot([i, i], [s["ageing_index_p10"], s["ageing_index_p90"]], color="black", lw=2)
    ax[2].set(title="Ageing index by municipality size (bar: pooled; line: 10th-90th percentile)", ylabel="per 100")
    ax[2].tick_params(axis="x", labelrotation=20)
    for a in ax:
        a.spines[["top", "right"]].set_visible(False)
    fig.savefig(path, dpi=100)
    plt.close(fig)


def render_bench(b: dict[str, Any]) -> str:
    env = b["environment"]
    out = [
        "# Benchmark",
        "",
        f"Run on {env['system']}, {env['cpus']} CPUs, Python {env['python']}, NumPy {env['numpy']}; seed {env['seed']}; each time is the median of {env['repeat']} runs; command `{env['command']}`.",
        "",
        "## 1. Reading the files",
        "",
        "| Files | Units | Rows | Size | Time | Rows per second |",
        "|---|---|---|---|---|---|",
    ]
    for r in b["reading"]:
        out.append(
            f"| {r['what']} | {r['units']:,} | {r['rows']:,} | {r['bytes'] / 1e6:,.1f} MB | {fmt_s(r['seconds'])} | {r['rows'] / r['seconds']:,.0f} |"
        )
    out += [
        "",
        "## 2. The indicators: NumPy against the literal implementation",
        "",
        "| Units | NumPy | Literal | Ratio |",
        "|---|---|---|---|",
    ]
    for r in b["indicators"]:
        lit = "-" if r["literal"] is None else fmt_s(r["literal"])
        ratio = "-" if r["literal"] is None else f"{r['literal'] / r['numpy']:,.0f}x"
        out.append(f"| {r['units']:,} | {fmt_s(r['numpy'])} | {lit} | {ratio} |")
    out += [
        "",
        "## 3. The whole report",
        "",
        f"Building the report of Piemonte from the loaded tables takes {fmt_s(b['report']['seconds'])}.",
        "",
        "## 4. Agreement",
        "",
    ]
    v = b["verification"]
    out.append(
        f"{v['checks']} comparisons (the three real tables and {v['checks'] - 3} random ones): {v['numbers']:,} values compared, the largest relative difference is {v['worst']:.2e}. "
        + ("All agree." if v["ok"] else "THEY DISAGREE.")
    )
    out.append("")
    return "\n".join(out)


def bench_figure(b: dict[str, Any], path: Path) -> None:
    fig, ax = plt.subplots(1, 2, figsize=(13, 5), constrained_layout=True)
    rows = b["indicators"]
    ax[0].plot([r["units"] for r in rows], [r["numpy"] for r in rows], "o-", color=COLORS["main"], label="NumPy")
    lit = [r for r in rows if r["literal"] is not None]
    ax[0].plot([r["units"] for r in lit], [r["literal"] for r in lit], "s--", color=COLORS["italy"], label="literal")
    ax[0].set(xscale="log", yscale="log", title="Indicators: time by number of units", xlabel="units", ylabel="seconds")
    ax[0].legend(frameon=False)
    rd = b["reading"]
    ax[1].bar([r["what"] for r in rd], [r["rows"] / r["seconds"] for r in rd], color=COLORS["second"])
    ax[1].set(title="Reading: rows per second", ylabel="rows / s")
    ax[1].tick_params(axis="x", labelrotation=15)
    for a in ax:
        a.spines[["top", "right"]].set_visible(False)
    fig.savefig(path, dpi=100)
    plt.close(fig)
