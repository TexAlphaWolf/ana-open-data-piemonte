"""Command line: check-data, report, indicators, comune, verify, bench, render."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

from odpiemonte import __version__, analysis, bench, indicators, report, verify
from odpiemonte.data import Dataset, data_dir, load_dataset, verify_hashes
from odpiemonte.load import DataError

Error = (DataError, OSError, ValueError)
LEVELS = ("comune", "provincia", "regione")


def summary_lines(rep: dict[str, Any]) -> list[str]:
    p = rep["piemonte"]
    i, it = p["indicators"], p["italy"]
    est = ", estimate" if rep["estimate"] else ""
    return [
        f"Piemonte, ISTAT 1 January {rep['year']}{est}: {p['comuni']:,} municipalities, {p['population']:,} residents",
        f"median age {i['median_age']:.1f} (Italy {it['median_age']:.1f}), aged 65+ {i['share_65_plus']:.1f}% (Italy {it['share_65_plus']:.1f}%), "
        f"ageing index {i['ageing_index']:.1f} (Italy {it['ageing_index']:.1f}), rank {p['ageing_rank_of_20']} of 20 regions",
        "oldest province by ageing index: "
        + max(rep["provinces"], key=lambda r: r["indicators"]["ageing_index"])["name"]
        + ", youngest: "
        + min(rep["provinces"], key=lambda r: r["indicators"]["ageing_index"])["name"],
        "the municipalities, provinces and regions add up to the same population",
    ]


def cmd_check_data(a: argparse.Namespace) -> int:
    folder = data_dir(a.data)
    ds = load_dataset(folder)
    print(
        f"{folder}: {len(ds.files)} files read, year {ds.comuni.year}: {len(ds.comuni):,} municipalities, {len(ds.provinces)} provinces, {len(ds.regions)} regions"
    )
    analysis.reconcile(ds)
    print("the municipalities, provinces and regions add up to the same population")
    manifest = Path(a.manifest) if a.manifest else folder.parent / "SHA256SUMS"
    if manifest.is_file():
        bad = verify_hashes(folder, manifest)
        for line in bad:
            print(f"hash: {line}")
        if bad:
            return 1
        print(f"hashes: all files are as published ({manifest.name})")
    return 0


def cmd_report(a: argparse.Namespace) -> int:
    ds = load_dataset(data_dir(a.data))
    rep = analysis.build_report(ds, f"ISTAT POSAS {ds.comuni.year}")
    for line in summary_lines(rep):
        print(line)
    if a.out:
        out = Path(a.out)
        out.mkdir(parents=True, exist_ok=True)
        (out / "report.json").write_text(json.dumps(rep, indent=1) + "\n", encoding="utf-8")
        (out / "report.md").write_text(report.render_report(rep), encoding="utf-8")
        report.report_figure(rep, out / "summary.png")
        print(f"written: {out / 'report.json'}, {out / 'report.md'}, {out / 'summary.png'}")
    return 0


def _table(ds: Dataset, level: str) -> Any:
    return {"comune": ds.comuni, "provincia": ds.provinces, "regione": ds.regions}[level]


def cmd_indicators(a: argparse.Namespace) -> int:
    ds = load_dataset(data_dir(a.data))
    t = _table(ds, a.level)
    ix = indicators.compute(t.counts)
    if a.sort not in ix:
        raise ValueError(f"--sort must be one of {', '.join(ix)}")
    keep = np.where(ix["population"] >= a.min_population)[0]
    key = np.nan_to_num(ix[a.sort][keep], nan=-np.inf)
    order = keep[np.argsort(key if a.ascending else -key, kind="stable")][: a.top]
    print(f"{'code':<7}{'name':<30}{'residents':>10}{'median':>8}{'65+ %':>7}{'ageing':>8}{'depend.':>8}")
    for i in order:
        print(
            f"{t.codes[i]:<7}{t.names[i][:29]:<30}{ix['population'][i]:>10,.0f}{ix['median_age'][i]:>8.1f}{ix['share_65_plus'][i]:>7.1f}"
            + (f"{ix['ageing_index'][i]:>8.1f}" if not np.isnan(ix["ageing_index"][i]) else f"{'-':>8}")
            + f"{ix['dependency'][i]:>8.1f}"
        )
    return 0


def cmd_comune(a: argparse.Namespace) -> int:
    ds = load_dataset(data_dir(a.data))
    pm = ds.comuni
    hits = [i for i in range(len(pm)) if pm.codes[i] == a.who or pm.names[i].lower() == a.who.lower()]
    if not hits:
        raise DataError(f"no municipality of Piemonte called or coded '{a.who}'")
    for i in hits:
        ix = indicators.compute(pm.counts[i : i + 1])
        print(f"{pm.names[i]} ({pm.codes[i]}), province {ds.provinces.names[ds.provinces.index(pm.codes[i][:3])]}")
        for k, what in indicators.INDICATORS.items():
            v = ix[k][0]
            print(f"  {k:<22}{'-' if np.isnan(v) else f'{v:,.1f}':>10}   {what}")
        by = pm.counts[i].sum(axis=0)
        print(
            "  residents by ten-year class: "
            + ", ".join(f"{lo}-{lo + 9}: {int(by[lo : lo + 10].sum())}" for lo in range(0, 100, 10))
            + f", 100+: {int(by[100])}"
        )
    return 0


def cmd_verify(a: argparse.Namespace) -> int:
    ds = load_dataset(data_dir(a.data)) if not a.random_only else None
    results = verify.run(ds, a.draws, a.seed)
    bad = [c for c in results if not c.ok]
    for c in results:
        print(
            f"{'ok  ' if c.ok else 'FAIL'} {c.name}: {c.units} units, {c.numbers:,} values, largest relative difference {c.worst:.1e}"
        )
    print(f"{len(results) - len(bad)} of {len(results)} comparisons agree with the literal implementation")
    return 1 if bad else 0


def cmd_bench(a: argparse.Namespace) -> int:
    sizes = [int(p.replace("_", "")) for p in a.sizes.split(",") if p.strip()]
    if any(s < 100 for s in sizes):
        raise ValueError("--sizes needs whole numbers of 100 or more")
    result = bench.run_bench(
        data_dir(a.data), sizes, a.ref_max, a.repeat, a.draws, a.seed, a.cmdline,
        Path(a.national) if a.national else None, lambda m: print(m, flush=True),
    )  # fmt: skip
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "bench.json").write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    (out / "bench.md").write_text(report.render_bench(result), encoding="utf-8")
    report.bench_figure(result, out / "summary.png")
    print(f"written: {out / 'bench.json'}, {out / 'bench.md'}, {out / 'summary.png'}")
    return 0 if result["verification"]["ok"] else 1


def cmd_render(a: argparse.Namespace) -> int:
    try:
        data = json.loads(Path(a.file).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DataError(f"cannot read {a.file}: {exc}") from exc
    kind = data.get("kind") if isinstance(data, dict) else None
    if kind not in ("report", "bench"):
        raise DataError(f"{a.file} is neither a report.json nor a bench.json")
    text = report.render_report(data) if kind == "report" else report.render_bench(data)
    if a.output:
        Path(a.output).write_text(text, encoding="utf-8")
        print(f"written: {a.output}")
    else:
        print(text, end="")
    if a.figure:
        (report.report_figure if kind == "report" else report.bench_figure)(data, Path(a.figure))
        print(f"written: {a.figure}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="odp", description="Open data analysis of Piemonte (ISTAT population by age and sex)."
    )
    p.add_argument("--version", action="version", version=f"odp {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    def add(name: str, func: Any, help_: str, data: bool = True) -> argparse.ArgumentParser:
        sp = sub.add_parser(name, help=help_)
        if data:
            sp.add_argument("--data", help="folder with the ISTAT POSAS files (default: $ODP_DATA, then data/istat)")
        sp.set_defaults(func=func)
        return sp

    s = add(
        "check-data", cmd_check_data, "read the files, check that the three levels add up and that the hashes match"
    )
    s.add_argument("--manifest", help="a sha256sum file (default: SHA256SUMS next to the folder)")
    s = add("report", cmd_report, "the analysis of Piemonte")
    s.add_argument("--out", help="write report.json, report.md and summary.png here")
    s = add("indicators", cmd_indicators, "the indicators of the units of a level, sorted")
    s.add_argument("--level", choices=LEVELS, default="comune")
    s.add_argument("--sort", default="ageing_index")
    s.add_argument("--ascending", action="store_true")
    s.add_argument("--top", type=int, default=10)
    s.add_argument("--min-population", type=int, default=1000)
    s = add("comune", cmd_comune, "the indicators of one municipality of Piemonte")
    s.add_argument("who", help="the name or the 6-digit ISTAT code")
    s = add("verify", cmd_verify, "compare the NumPy indicators with the literal ones")
    s.add_argument("--draws", type=int, default=25)
    s.add_argument("--seed", type=int, default=1)
    s.add_argument("--random-only", action="store_true", help="do not read the data, compare on random tables only")
    s = add("bench", cmd_bench, "speed of reading and of the indicators, and the agreement")
    s.add_argument(
        "--sizes",
        default="10000,100000",
        help="numbers of units to time the indicators on (the real 1,180 are always first)",
    )
    s.add_argument("--ref-max", type=int, default=100000, help="largest size on which the literal version is timed")
    s.add_argument("--repeat", type=int, default=5)
    s.add_argument("--draws", type=int, default=50)
    s.add_argument("--seed", type=int, default=1)
    s.add_argument("--national", help="also time reading the national municipalities file (POSAS_*_it_Comuni.csv)")
    s.add_argument("--out", default="odp-out")
    s = add("render", cmd_render, "rebuild the Markdown (and figure) from a report.json or bench.json", data=False)
    s.add_argument("file")
    s.add_argument("-o", "--output")
    s.add_argument("--figure")
    return p


def main(argv: list[str] | None = None) -> int:
    given = sys.argv[1:] if argv is None else argv
    args = build_parser().parse_args(given)
    args.cmdline = " ".join(given)
    try:
        return int(args.func(args))
    except Error as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
