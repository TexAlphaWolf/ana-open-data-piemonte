from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from odpiemonte.load import MAX_AGE, DataError, Table, concat, read_posas

from .conftest import at, flat, posas_text, write


def test_reads_a_file_and_keeps_the_ages(tmp_path: Path) -> None:
    m, f = at(10, 3, 4)
    t = read_posas(write(tmp_path / "a.csv", {"001001": ("Agliè", m, f), "001002": ("Bo", *at(100, 1, 0))}), "comune")
    assert (t.year, t.estimate, t.codes, t.names) == (2026, True, ["001001", "001002"], ["Agliè", "Bo"])
    assert t.counts.shape == (2, 2, MAX_AGE + 1)
    assert t.counts[0, 0, 10] == 3 and t.counts[0, 1, 10] == 4 and t.counts[1, 0, 100] == 1 and t.total() == 8


def test_rows_may_be_interleaved_like_the_two_castro(tmp_path: Path) -> None:
    """In the national file two municipalities called Castro are mixed row by row: units are told apart by code."""
    units = {"016065": ("Castro", *flat(1, 2, 1)), "075096": ("Castro", *flat(1, 5, 7))}
    t = read_posas(write(tmp_path / "a.csv", units, order="age"), "comune")
    assert t.codes == ["016065", "075096"] and t.names == ["Castro", "Castro"]
    assert t.counts[0].sum() == 3 * (MAX_AGE + 1) and t.counts[1].sum() == 12 * (MAX_AGE + 1)


def test_levels_have_their_own_code_width(tmp_path: Path) -> None:
    p = write(
        tmp_path / "p.csv",
        {"001": ("Torino", *flat(1))},
        header='"Codice provincia";"Provincia";"Età";"Totale maschi";"Totale femmine";"Totale"',
    )
    assert read_posas(p, "provincia").codes == ["001"]
    with pytest.raises(DataError, match="expected the header"):
        read_posas(p, "comune")
    wide = write(
        tmp_path / "w.csv",
        {"1": ("Torino", *flat(1))},
        header='"Codice provincia";"Provincia";"Et\u00e0";"Totale maschi";"Totale femmine";"Totale"',
    )
    with pytest.raises(DataError, match="3-digit"):
        read_posas(wide, "provincia")
    with pytest.raises(DataError):
        read_posas(p, "paese")


def lines_of(units: dict[str, tuple[str, list[int], list[int]]]) -> list[str]:
    return posas_text(units).lstrip("﻿").splitlines()


def bad(tmp_path: Path, mutate: object, match: str) -> None:
    lines = lines_of({"001001": ("A", *flat(1))})
    mutate(lines)  # type: ignore[operator]
    p = tmp_path / "bad.csv"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(DataError, match=match):
        read_posas(p, "comune")


def test_every_irregularity_is_an_error_that_names_the_line(tmp_path: Path) -> None:
    bad(tmp_path, lambda ls: ls.__setitem__(0, '"Something else"'), r"bad.csv:1: not a POSAS title")
    bad(tmp_path, lambda ls: ls.__setitem__(1, '"Codice";"Comune"'), r"bad.csv:2: expected the header")
    bad(tmp_path, lambda ls: ls.__setitem__(2, '"1001";"A";0;1;1;2'), r"bad.csv:3: '1001' is not a 6-digit code")
    bad(tmp_path, lambda ls: ls.__setitem__(2, '"001001";"A";0;1;1;3'), r"bad.csv:3: 1 \+ 1 is not 3")
    bad(tmp_path, lambda ls: ls.__setitem__(2, '"001001";"A";x;1;1;2'), r"bad.csv:3: 'x' is not a whole number")
    bad(tmp_path, lambda ls: ls.__setitem__(2, '"001001";"A";0;-1;3;2'), r"is not a whole number")
    bad(tmp_path, lambda ls: ls.__setitem__(2, '"001001";"A";0;1;1'), r"bad.csv:3: expected 6 fields, found 5")
    bad(tmp_path, lambda ls: ls.__setitem__(3, ls[2]), r"has age 0 twice")
    bad(tmp_path, lambda ls: ls.__setitem__(2, '"001001";"A";101;1;1;2'), r"age 101 is not 0 to 100 or 999")
    bad(tmp_path, lambda ls: ls.__setitem__(3, '"001001";"B";1;1;1;2'), r"is called 'B' and 'A'")
    bad(tmp_path, lambda ls: ls.pop(5), r"is missing ages \[3\]")
    bad(tmp_path, lambda ls: ls.__setitem__(-2, '"001001";"A";999;99;99;198'), r"is not the sum of the ages")
    bad(tmp_path, lambda ls: ls.__delitem__(slice(2, None)), r"too short")


def test_a_file_with_no_units_or_that_cannot_be_read(tmp_path: Path) -> None:
    p = tmp_path / "e.csv"
    p.write_text(
        lines_of({"001001": ("A", *flat(1))})[0]
        + "\n"
        + lines_of({"001001": ("A", *flat(1))})[1]
        + "\n"
        + '"Nota: x"\n',
        encoding="utf-8",
    )
    with pytest.raises(DataError, match="no data"):
        read_posas(p, "comune")
    with pytest.raises(DataError, match="cannot be read"):
        read_posas(tmp_path / "missing.csv", "comune")
    p.write_bytes(b"\xff\xfe\x00")
    with pytest.raises(DataError, match="cannot be read"):
        read_posas(p, "comune")


def test_select_prefix_index_and_concat(tmp_path: Path) -> None:
    a = read_posas(write(tmp_path / "a.csv", {"001001": ("A", *flat(1)), "001002": ("B", *flat(1))}), "comune")
    b = read_posas(write(tmp_path / "b.csv", {"002001": ("C", *flat(2))}), "comune")
    t = concat([a, b])
    assert t.codes == ["001001", "001002", "002001"] and len(t) == 3
    assert t.with_prefix("001").codes == ["001001", "001002"] and t.with_prefix("002", "009").names == ["C"]
    assert t.index("002001") == 2
    with pytest.raises(DataError):
        t.index("999999")
    with pytest.raises(DataError, match="more than one"):
        concat([a, a])
    other = Table("provincia", 2026, True, ["001"], ["X"], a.counts[:1])
    with pytest.raises(DataError, match="different"):
        concat([a, other])
    with pytest.raises(DataError):
        concat([])
    assert np.array_equal(t.select(np.array([False, False, True])).counts, b.counts)
