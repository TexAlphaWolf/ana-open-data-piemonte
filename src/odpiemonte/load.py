"""Strict reader for the ISTAT "POSAS" files: resident population by age and sex on 1 January, for municipalities,
provinces or regions. Every irregularity is an error that names the file and the line."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import numpy.typing as npt

MAX_AGE = 100  # the last class is "100 and over"
AGE_TOTAL = 999  # ISTAT's own total row of each unit
LEVELS = {
    "comune": ("Codice comune", "Comune", 6),
    "provincia": ("Codice provincia", "Provincia", 3),
    "regione": ("Codice regione", "Regione", 2),
}
TITLE = re.compile(r"^Popolazione residente per et. e sesso al 1. gennaio (\d{4})(?: \((\w+)\))?$")
COLUMNS = ("Età", "Totale maschi", "Totale femmine", "Totale")


class DataError(ValueError):
    """A file that does not look like what it should."""


@dataclass
class Table:
    """The population of many units: `counts[i, sex, age]`, sex 0 = male, 1 = female, age 0 to 100 (100 = 100 and over)."""

    level: str
    year: int
    estimate: bool
    codes: list[str]
    names: list[str]
    counts: npt.NDArray[np.int64]

    def __len__(self) -> int:
        return len(self.codes)

    def total(self) -> int:
        return int(self.counts.sum())

    def index(self, code: str) -> int:
        try:
            return self.codes.index(code)
        except ValueError:
            raise DataError(f"no unit with code {code}") from None

    def select(self, mask: npt.NDArray[np.bool_]) -> Table:
        keep = [i for i in range(len(self)) if mask[i]]
        return Table(
            self.level,
            self.year,
            self.estimate,
            [self.codes[i] for i in keep],
            [self.names[i] for i in keep],
            self.counts[keep],
        )

    def with_prefix(self, *prefixes: str) -> Table:
        """The units whose code starts with one of the prefixes (the municipalities of a province, say)."""
        return self.select(np.array([c.startswith(prefixes) for c in self.codes], dtype=bool))


def _int(text: str, where: str) -> int:
    if not text.isascii() or not text.isdigit():
        raise DataError(f"{where}: '{text}' is not a whole number")
    return int(text)


def read_posas(path: str | Path, level: str) -> Table:
    """Read one POSAS file. `level` is `comune`, `provincia` or `regione`."""
    if level not in LEVELS:
        raise DataError(f"unknown level '{level}'")
    code_col, name_col, width = LEVELS[level]
    p = Path(path)
    try:
        text = p.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        raise DataError(f"{p}: cannot be read: {exc}") from exc
    lines = text.splitlines()
    if len(lines) < 3:
        raise DataError(f"{p}: too short")
    title = next(csv.reader([lines[0]], delimiter=";"))
    m = TITLE.match(title[0]) if len(title) == 1 else None
    if m is None:
        raise DataError(f"{p}:1: not a POSAS title: {lines[0]!r}")
    year, estimate = int(m.group(1)), m.group(2) is not None
    header = next(csv.reader([lines[1]], delimiter=";"))
    if header != [code_col, name_col, *COLUMNS]:
        raise DataError(f"{p}:2: expected the header {[code_col, name_col, *COLUMNS]}, found {header}")

    # Rows are grouped by code, not by position: in the national file two municipalities with the same name (the two
    # Castro) are interleaved row by row, so the reader never assumes that the rows of a unit are next to each other.
    index: dict[str, int] = {}
    codes: list[str] = []
    names: list[str] = []
    blocks: list[np.ndarray] = []
    seen: list[np.ndarray] = []  # which ages (0 to 100, then the total at 101) were read
    totals: list[tuple[int, int]] = []
    for no, row in enumerate(csv.reader(lines[2:], delimiter=";"), start=3):
        where = f"{p}:{no}"
        if len(row) == 1 and row[0].startswith("Nota:"):
            continue
        if len(row) != 6:
            raise DataError(f"{where}: expected 6 fields, found {len(row)}")
        code, name = row[0], row[1]
        if len(code) != width or not code.isdigit():
            raise DataError(f"{where}: '{code}' is not a {width}-digit code")
        age = _int(row[2], where)
        male, female, both = (_int(x, where) for x in row[3:])
        if male + female != both:
            raise DataError(f"{where}: {male} + {female} is not {both}")
        i = index.get(code)
        if i is None:
            i = index[code] = len(codes)
            codes.append(code)
            names.append(name)
            blocks.append(np.zeros((2, MAX_AGE + 1), dtype=np.int64))
            seen.append(np.zeros(MAX_AGE + 2, dtype=bool))
            totals.append((0, 0))
        elif name != names[i]:
            raise DataError(f"{where}: {code} is called '{name}' and '{names[i]}'")
        if age != AGE_TOTAL and not 0 <= age <= MAX_AGE:
            raise DataError(f"{where}: age {age} is not 0 to {MAX_AGE} or {AGE_TOTAL}")
        slot = MAX_AGE + 1 if age == AGE_TOTAL else age
        if seen[i][slot]:
            raise DataError(f"{where}: {code} has age {age} twice")
        seen[i][slot] = True
        if age == AGE_TOTAL:
            totals[i] = (male, female)
        else:
            blocks[i][0, age], blocks[i][1, age] = male, female
    for i, code in enumerate(codes):
        if not seen[i].all():
            missing = [a for a in range(MAX_AGE + 1) if not seen[i][a]] + (
                [AGE_TOTAL] if not seen[i][MAX_AGE + 1] else []
            )
            raise DataError(f"{p}: {code} {names[i]} is missing ages {missing[:5]}")
        got = (int(blocks[i][0].sum()), int(blocks[i][1].sum()))
        if got != totals[i]:
            raise DataError(f"{p}: {code} {names[i]}: the total row {totals[i]} is not the sum of the ages {got}")
    if not codes:
        raise DataError(f"{p}: no data")
    return Table(level, year, estimate, codes, names, np.stack(blocks))


def concat(tables: list[Table]) -> Table:
    """Put the tables of several files (the provinces of a region) together."""
    if not tables:
        raise DataError("nothing to put together")
    first = tables[0]
    for t in tables[1:]:
        if (t.level, t.year, t.estimate) != (first.level, first.year, first.estimate):
            raise DataError("files of different levels or years cannot be put together")
    codes = [c for t in tables for c in t.codes]
    if len(set(codes)) != len(codes):
        raise DataError("a code appears in more than one file")
    return Table(
        first.level,
        first.year,
        first.estimate,
        codes,
        [n for t in tables for n in t.names],
        np.concatenate([t.counts for t in tables]),
    )
