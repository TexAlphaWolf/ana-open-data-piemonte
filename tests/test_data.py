from __future__ import annotations

import shutil
from pathlib import Path

import numpy as np
import pytest

from odpiemonte import analysis
from odpiemonte.data import PIEMONTE_PROVINCES, data_dir, load_dataset, province_files, verify_hashes
from odpiemonte.load import DataError

from .conftest import DATA, ROOT


def test_the_shipped_files_are_the_published_ones() -> None:
    assert verify_hashes(DATA, ROOT / "data" / "SHA256SUMS") == []


def test_a_changed_or_missing_file_is_reported(tmp_path: Path) -> None:
    shutil.copytree(DATA, tmp_path / "istat")
    shutil.copy(ROOT / "data" / "SHA256SUMS", tmp_path / "SHA256SUMS")
    f = tmp_path / "istat" / "POSAS_2026_it_Regioni.csv"
    f.write_bytes(f.read_bytes() + b" ")
    (tmp_path / "istat" / "POSAS_2026_it_005_Asti.csv").unlink()
    (tmp_path / "SHA256SUMS").write_text((tmp_path / "SHA256SUMS").read_text() + "\n", encoding="utf-8")
    assert sorted(verify_hashes(tmp_path / "istat", tmp_path / "SHA256SUMS")) == [
        "POSAS_2026_it_005_Asti.csv: missing",
        "POSAS_2026_it_Regioni.csv: changed",
    ]
    with pytest.raises(DataError):
        verify_hashes(tmp_path, tmp_path / "nope")


def test_the_real_dataset() -> None:
    ds = load_dataset(DATA)
    assert (ds.comuni.year, ds.comuni.estimate) == (2026, True)
    assert len(ds.comuni) == 1180 and ds.comuni.total() == 4_255_006
    assert (
        len(ds.provinces) == 107 and len(ds.regions) == 20 and ds.provinces.total() == ds.regions.total() == 58_942_828
    )
    assert sorted({c[:3] for c in ds.comuni.codes}) == sorted(PIEMONTE_PROVINCES)
    assert len(ds.files) == 10


def test_the_three_levels_add_up() -> None:
    r = analysis.reconcile(load_dataset(DATA))
    assert r["all_equal"] and r["italy"]["equal_by_age_and_sex"]
    assert [p["comuni_total"] for p in r["provinces"]] == [
        2_204_779,
        166_166,
        365_930,
        582_109,
        207_059,
        408_063,
        168_223,
        152_677,
    ]


def test_an_inconsistent_dataset_is_refused() -> None:
    ds = load_dataset(DATA)
    ds.comuni.counts[0, 0, 40] += 1
    with pytest.raises(DataError, match="do not add up"):
        analysis.reconcile(ds)
    ds = load_dataset(DATA)
    ds.regions.counts[3, 1, 0] += 1
    with pytest.raises(DataError):
        analysis.reconcile(ds)


def test_folder_and_file_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(DataError, match="no such folder"):
        data_dir(str(tmp_path / "nope"))
    monkeypatch.setenv("ODP_DATA", str(DATA))
    assert data_dir() == DATA and data_dir(str(tmp_path)) == tmp_path
    with pytest.raises(DataError, match="expected one POSAS file for province 001"):
        province_files(tmp_path)
    shutil.copytree(DATA, tmp_path / "d")
    (tmp_path / "d" / "POSAS_2026_it_Regioni.csv").unlink()
    with pytest.raises(DataError, match=r"Province\.csv and POSAS"):
        load_dataset(tmp_path / "d")
    shutil.rmtree(tmp_path / "d")
    shutil.copytree(DATA, tmp_path / "d")
    text = (tmp_path / "d" / "POSAS_2026_it_Regioni.csv").read_text(encoding="utf-8").replace("2026", "2025", 1)
    (tmp_path / "d" / "POSAS_2026_it_Regioni.csv").write_text(text, encoding="utf-8")
    with pytest.raises(DataError, match="same year"):
        load_dataset(tmp_path / "d")


def test_real_data_properties() -> None:
    ds = load_dataset(DATA)
    both = ds.comuni.counts.sum(axis=1)
    assert both.min() >= 0 and (both.sum(axis=1) > 0).all()  # every municipality has residents
    assert np.array_equal(ds.comuni.counts.sum(axis=0).sum(axis=0)[:3] > 0, [True, True, True])
