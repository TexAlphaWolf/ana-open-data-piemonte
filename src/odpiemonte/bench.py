"""Speed of reading and of the indicators, and the agreement of the two implementations."""

from __future__ import annotations

import platform
import statistics
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np

from odpiemonte import analysis, indicators, reference, verify
from odpiemonte.data import Dataset, load_dataset, province_files
from odpiemonte.load import read_posas


def timed(fn: Callable[[], object], repeat: int) -> float:
    """The median time of `repeat` runs, in seconds."""
    runs = []
    for _ in range(repeat):
        t0 = time.perf_counter()
        fn()
        runs.append(time.perf_counter() - t0)
    return statistics.median(runs)


def _rows(path: Path) -> int:
    with path.open("rb") as f:
        return sum(1 for line in f if line[:1] == b'"' and line.count(b";") == 5) - 1  # the header is one of them


def reading(folder: Path, national: Path | None, repeat: int) -> list[dict[str, Any]]:
    out = []
    pf = province_files(folder)
    extra = sorted(folder.glob("POSAS_*_it_Province.csv")) + sorted(folder.glob("POSAS_*_it_Regioni.csv"))
    jobs: list[tuple[str, list[tuple[Path, str]]]] = [
        ("Piemonte, 8 province files", [(f, "comune") for f in pf]),
        ("all provinces and regions", [(extra[0], "provincia"), (extra[1], "regione")]),
    ]
    if national is not None:
        jobs.append(("Italy, all municipalities", [(national, "comune")]))
    for what, files in jobs:
        tables = [read_posas(f, lvl) for f, lvl in files]
        out.append(
            {
                "what": what,
                "units": sum(len(t) for t in tables),
                "rows": sum(_rows(f) for f, _ in files),
                "bytes": sum(f.stat().st_size for f, _ in files),
                "seconds": timed(lambda files=files: [read_posas(f, lvl) for f, lvl in files], repeat),  # type: ignore[misc]
            }
        )
    return out


def run_bench(
    folder: Path,
    sizes: list[int],
    ref_max: int,
    repeat: int,
    draws: int,
    seed: int,
    command: str,
    national: Path | None = None,
    progress: Callable[[str], None] = lambda _m: None,
) -> dict[str, Any]:
    t0 = time.perf_counter()
    progress("reading the files")
    rd = reading(folder, national, repeat)
    ds: Dataset = load_dataset(folder)
    progress("indicators by number of units")
    base = ds.comuni.counts
    rows = []
    for n in [len(base), *sizes]:
        counts = base if n == len(base) else np.resize(base, (n, *base.shape[1:]))
        rows.append(
            {
                "units": int(n),
                "real": n == len(base),
                "numpy": timed(lambda c=counts: indicators.compute(c), repeat),  # type: ignore[misc]
                "literal": timed(lambda c=counts: reference.compute(c), max(1, repeat // 2)) if n <= ref_max else None,  # type: ignore[misc]
            }
        )
    progress("the whole report")
    rep_s = timed(lambda: analysis.build_report(ds), repeat)
    progress("agreement of the two implementations")
    checks = verify.run(ds, draws, seed)
    return {
        "kind": "bench",
        "environment": {
            "odpiemonte": "1.0.0",
            "python": platform.python_version(),
            "numpy": np.__version__,
            "system": f"{platform.system()} {platform.machine()}",
            "cpus": __import__("os").cpu_count(),
            "seed": seed,
            "repeat": repeat,
            "command": command,
            "seconds": round(time.perf_counter() - t0, 1),
        },
        "reading": rd,
        "indicators": rows,
        "report": {"seconds": rep_s},
        "verification": {
            "checks": len(checks),
            "numbers": sum(c.numbers for c in checks),
            "worst": max(c.worst for c in checks),
            "ok": all(c.ok for c in checks),
            "bad": sum(1 for c in checks if not c.ok),
        },
    }
