"""Where the data is, and the three tables an analysis needs: the municipalities of Piemonte, all provinces and all regions."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path

from odpiemonte.load import DataError, Table, concat, read_posas

PIEMONTE_REGION = "01"
# The province files of Piemonte, by the code of the province (the number in the file name).
PIEMONTE_PROVINCES = ("001", "002", "003", "004", "005", "006", "096", "103")
ENV = "ODP_DATA"
DEFAULT = "data/istat"


def data_dir(given: str | None = None) -> Path:
    """The folder with the ISTAT files: the option, else the environment variable `ODP_DATA`, else `data/istat`."""
    path = Path(given or os.environ.get(ENV) or DEFAULT)
    if not path.is_dir():
        raise DataError(
            f"{path}: no such folder (give --data, or set {ENV}; the repository keeps the files in {DEFAULT})"
        )
    return path


def province_files(folder: Path) -> list[Path]:
    """The POSAS files of the provinces of Piemonte, in code order."""
    out = []
    for code in PIEMONTE_PROVINCES:
        found = sorted(folder.glob(f"POSAS_*_it_{code}_*.csv"))
        if len(found) != 1:
            raise DataError(f"{folder}: expected one POSAS file for province {code}, found {len(found)}")
        out.append(found[0])
    return out


@dataclass
class Dataset:
    comuni: Table  # the municipalities of Piemonte
    provinces: Table  # every province of Italy
    regions: Table  # every region of Italy
    files: list[str]


def load_dataset(folder: Path) -> Dataset:
    files = province_files(folder)
    year_files = sorted(folder.glob("POSAS_*_it_Province.csv")) + sorted(folder.glob("POSAS_*_it_Regioni.csv"))
    if len(year_files) != 2:
        raise DataError(f"{folder}: expected POSAS_*_it_Province.csv and POSAS_*_it_Regioni.csv")
    comuni = concat([read_posas(f, "comune") for f in files])
    provinces = read_posas(year_files[0], "provincia")
    regions = read_posas(year_files[1], "regione")
    if not comuni.year == provinces.year == regions.year:
        raise DataError("the files are not all of the same year")
    return Dataset(comuni, provinces, regions, [f.name for f in [*files, *year_files]])


def verify_hashes(folder: Path, manifest: Path) -> list[str]:
    """Check the files against a `sha256sum` manifest. Returns what is wrong (empty if all is well)."""
    problems = []
    try:
        lines = manifest.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise DataError(f"{manifest}: cannot be read: {exc}") from exc
    for line in lines:
        if not line.strip():
            continue
        digest, _, name = line.partition("  ")
        target = folder / name.strip().lstrip("*")
        if not target.is_file():
            problems.append(f"{name}: missing")
        elif hashlib.sha256(target.read_bytes()).hexdigest() != digest:
            problems.append(f"{name}: changed")
    return problems
