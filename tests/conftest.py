from __future__ import annotations

import os
from pathlib import Path

import numpy as np

from odpiemonte.load import MAX_AGE

SEED = int(os.environ.get("ODP_TEST_SEED", "1"))
DRAWS = int(os.environ.get("ODP_TEST_DRAWS", "10"))
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "istat"

TITLE = '"Popolazione residente per età e sesso al 1° gennaio 2026 (stima)"'
HEADER = '"Codice comune";"Comune";"Età";"Totale maschi";"Totale femmine";"Totale"'


def posas_text(units: dict[str, tuple[str, list[int], list[int]]], header: str = HEADER, order: str = "unit") -> str:
    """A POSAS file for the units `{code: (name, males by age, females by age)}`. `order="age"` interleaves them by age."""
    rows: list[tuple[int, str, str]] = []
    for code, (name, males, females) in units.items():
        for a in range(MAX_AGE + 1):
            rows.append((a, code, f'"{code}";"{name}";{a};{males[a]};{females[a]};{males[a] + females[a]}'))
        rows.append((999, code, f'"{code}";"{name}";999;{sum(males)};{sum(females)};{sum(males) + sum(females)}'))
    if order == "age":
        rows.sort(key=lambda r: r[0])
    lines = [TITLE, header, *[r[2] for r in rows], '"Nota: lo stato civile è in corso di validazione."']
    return "﻿" + "\n".join(lines) + "\n"


def flat(n: int, males: int = 1, females: int = 1) -> tuple[list[int], list[int]]:
    return [males] * (MAX_AGE + 1), [females] * (MAX_AGE + 1)


def at(age: int, males: int = 0, females: int = 0) -> tuple[list[int], list[int]]:
    """Everyone at one age."""
    m, f = [0] * (MAX_AGE + 1), [0] * (MAX_AGE + 1)
    m[age], f[age] = males, females
    return m, f


def counts_of(*units: tuple[list[int], list[int]]) -> np.ndarray:
    return np.array([[m, f] for m, f in units], dtype=np.int64)


def write(path: Path, units: dict[str, tuple[str, list[int], list[int]]], **kw: str) -> Path:
    path.write_text(posas_text(units, **kw), encoding="utf-8")
    return path
