from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from odpiemonte.cli import main

from .conftest import DATA, ROOT


def run(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, str, str]:
    code = main(list(argv))
    cap = capsys.readouterr()
    return code, cap.out, cap.err


@pytest.fixture(autouse=True)
def data_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ODP_DATA", str(DATA))


def test_check_data(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    code, out, _ = run(capsys, "check-data")
    assert (
        code == 0
        and "1,180 municipalities, 107 provinces, 20 regions" in out
        and "add up to the same population" in out
    )
    assert "hashes: all files are as published" in out
    shutil.copytree(DATA, tmp_path / "istat")
    f = tmp_path / "istat" / "POSAS_2026_it_Regioni.csv"
    f.write_bytes(f.read_bytes() + b'"Nota: changed"\n')
    shutil.copy(ROOT / "data" / "SHA256SUMS", tmp_path / "SHA256SUMS")
    code, out, _ = run(capsys, "check-data", "--data", str(tmp_path / "istat"))
    assert code == 1 and "POSAS_2026_it_Regioni.csv: changed" in out
    assert run(capsys, "check-data", "--data", str(tmp_path / "nope"))[0] == 2


def test_report(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    out_dir = tmp_path / "r"
    code, out, _ = run(capsys, "report", "--out", str(out_dir))
    assert code == 0 and "1,180 municipalities, 4,255,006 residents" in out and "rank 8 of 20 regions" in out
    rep = json.loads((out_dir / "report.json").read_text(encoding="utf-8"))
    assert rep["kind"] == "report" and (out_dir / "summary.png").stat().st_size > 10_000
    md = tmp_path / "again.md"
    assert run(capsys, "render", str(out_dir / "report.json"), "-o", str(md))[0] == 0
    assert md.read_text(encoding="utf-8") == (out_dir / "report.md").read_text(encoding="utf-8")
    assert "# Piemonte report" in run(capsys, "render", str(out_dir / "report.json"))[1]
    assert run(capsys, "render", str(out_dir / "report.json"), "--figure", str(tmp_path / "f.png"))[0] == 0
    (tmp_path / "bad.json").write_text('{"kind": "x"}', encoding="utf-8")
    assert run(capsys, "render", str(tmp_path / "bad.json"))[0] == 2
    assert run(capsys, "render", str(tmp_path / "missing.json"))[0] == 2


def test_indicators_and_comune(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = run(capsys, "indicators", "--top", "3")
    lines = out.splitlines()
    assert code == 0 and len(lines) == 4 and lines[1].startswith("006136 Ponzone")
    code, out, _ = run(
        capsys,
        "indicators",
        "--level",
        "regione",
        "--sort",
        "median_age",
        "--ascending",
        "--top",
        "2",
        "--min-population",
        "0",
    )
    assert code == 0 and out.splitlines()[1].split()[1] == "Campania"
    assert run(capsys, "indicators", "--sort", "nope")[0] == 2
    code, out, _ = run(capsys, "comune", "Biella")
    assert code == 0 and "Biella (096004), province Biella" in out and "ageing_index" in out
    assert "(006136)" in run(capsys, "comune", "006136")[1]
    assert run(capsys, "comune", "Atlantide")[0] == 2


def test_verify(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = run(capsys, "verify", "--draws", "3")
    assert code == 0 and "6 of 6 comparisons agree" in out
    code, out, _ = run(capsys, "verify", "--draws", "2", "--random-only")
    assert code == 0 and "2 of 2 comparisons agree" in out


def test_verify_fails_on_a_disagreement(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    from odpiemonte import reference

    real = reference.compute
    monkeypatch.setattr(reference, "compute", lambda c: {k: v * 1.001 for k, v in real(c).items()})
    code, out, _ = run(capsys, "verify", "--draws", "1", "--random-only")
    assert code == 1 and "FAIL" in out and "0 of 1 comparisons agree" in out


def test_bench_small(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    out = tmp_path / "b"
    code, text, _ = run(
        capsys, "bench", "--sizes", "200,400", "--ref-max", "400", "--repeat", "1", "--draws", "2", "--out", str(out)
    )
    assert code == 0 and "bench.json" in text
    b = json.loads((out / "bench.json").read_text(encoding="utf-8"))
    assert (
        b["kind"] == "bench" and b["verification"]["ok"] and [r["units"] for r in b["indicators"]] == [1180, 200, 400]
    )
    assert b["reading"][0]["rows"] == 1180 * 102 and b["reading"][0]["units"] == 1180
    assert (out / "summary.png").stat().st_size > 5_000 and "|" in (out / "bench.md").read_text(encoding="utf-8")
    assert run(capsys, "render", str(out / "bench.json"), "--figure", str(tmp_path / "bf.png"))[0] == 0
    assert run(capsys, "bench", "--sizes", "10", "--out", str(out))[0] == 2


def test_bench_with_a_national_file(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    code, _, _ = run(
        capsys,
        "bench",
        "--sizes",
        "200",
        "--ref-max",
        "0",
        "--repeat",
        "1",
        "--draws",
        "1",
        "--national",
        str(DATA / "POSAS_2026_it_001_Torino.csv"),
        "--out",
        str(tmp_path),
    )
    b = json.loads((tmp_path / "bench.json").read_text(encoding="utf-8"))
    assert (
        code == 0 and b["reading"][2]["what"] == "Italy, all municipalities" and b["indicators"][1]["literal"] is None
    )


def test_help_and_version_work(capsys: pytest.CaptureFixture[str]) -> None:
    for argv in (["--help"], ["--version"], ["bench", "--help"], ["indicators", "--help"], ["report", "--help"]):
        with pytest.raises(SystemExit) as e:
            main(argv)
        assert e.value.code == 0
    assert "odp 1.0.0" in capsys.readouterr().out
