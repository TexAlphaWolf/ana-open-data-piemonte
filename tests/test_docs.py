"""The documentation must say what the data and the measurements say."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from odpiemonte import analysis, cli
from odpiemonte.data import load_dataset
from odpiemonte.report import fmt_s

ROOT = Path(__file__).resolve().parent.parent
REPORT = json.loads((ROOT / "docs" / "report.json").read_text(encoding="utf-8"))
BENCH = json.loads((ROOT / "docs" / "bench.json").read_text(encoding="utf-8"))
README = (ROOT / "README.md").read_text(encoding="utf-8")
ANALYSIS = (ROOT / "docs" / "analysis.md").read_text(encoding="utf-8")
METHOD = (ROOT / "docs" / "method.md").read_text(encoding="utf-8")
ONE_LINE = re.compile(r"\s+")


def flat(text: str) -> str:
    return ONE_LINE.sub(" ", text.replace("**", ""))


def test_the_benchmark_is_what_the_text_says_it_is() -> None:
    env = BENCH["environment"]
    assert env["odpiemonte"] == "1.0.0" and env["seed"] == 1 and env["repeat"] == 5 and env["cpus"] == 12
    assert env["python"] == "3.14.10" and env["system"] == "Linux x86_64"
    assert BENCH["verification"] == {"checks": 53, "numbers": 42991, "worst": 0.0, "ok": True, "bad": 0}
    assert [r["units"] for r in BENCH["indicators"]] == [1180, 10000, 100000]
    assert BENCH["reading"][0]["rows"] == 120360 and BENCH["reading"][0]["units"] == 1180


def test_markdown_is_the_render_of_the_json(tmp_path: Path) -> None:
    for name in ("report", "bench"):
        out = tmp_path / f"{name}.md"
        assert cli.main(["render", str(ROOT / "docs" / f"{name}.json"), "-o", str(out)]) == 0
        assert out.read_text(encoding="utf-8") == (ROOT / "docs" / f"{name}.md").read_text(encoding="utf-8")


def test_the_report_is_what_the_data_gives_today() -> None:
    ds = load_dataset(ROOT / "data" / "istat")
    fresh = json.loads(json.dumps(analysis.build_report(ds, f"ISTAT POSAS {ds.comuni.year}")))
    assert fresh == REPORT


def test_figures_exist() -> None:
    for name in ("report.png", "bench.png"):
        assert (ROOT / "docs" / name).stat().st_size > 10_000


@pytest.mark.parametrize("name", ["README.md", "docs/analysis.md"])
def test_no_scaffold_left(name: str) -> None:
    text = (ROOT / name).read_text(encoding="utf-8")
    assert not re.search(
        r"work in progress|TODO|TBD|lorem|measurements pending|provisional|pre-measurement", text, re.I
    )


@pytest.mark.parametrize(
    "name", ["README.md", "docs/analysis.md", "docs/architecture.md", "docs/method.md", "docs/limitations.md"]
)
def test_local_links_resolve(name: str) -> None:
    path = ROOT / name
    for target in re.findall(r"\]\(([^)#\s]+)(?:#[^)]*)?\)", path.read_text(encoding="utf-8")):
        if target.startswith(("http://", "https://")):
            continue
        assert (path.parent / target).exists(), f"{name}: {target}"


def test_the_real_output_blocks_are_the_real_output(capsys: pytest.CaptureFixture[str]) -> None:
    for command, title in (
        (["report"], "`odp report`:"),
        (["comune", "Ponzone"], "`odp comune Ponzone` (the oldest municipality with at least 1,000 residents):"),
        (["verify", "--draws", "5"], "`odp verify --draws 5`:"),
    ):
        assert cli.main(command) == 0
        block = re.search(re.escape(title) + r"\n\n```text\n(.*?)```", README, re.S)
        assert block and block.group(1) == capsys.readouterr().out, command


def test_the_readme_numbers_are_the_measurements() -> None:
    p, it = REPORT["piemonte"]["indicators"], REPORT["piemonte"]["italy"]
    rd = BENCH["reading"][0]
    ind = {r["units"]: r for r in BENCH["indicators"]}
    ratios = [r["literal"] / r["numpy"] for r in ind.values()]
    must = [
        f"Median age {p['median_age']:.1f} against {it['median_age']:.1f}",
        f"{p['share_65_plus']:.1f}% aged 65 and over against {it['share_65_plus']:.1f}%",
        f"The ageing index is {p['ageing_index']:.1f} against {it['ageing_index']:.1f}",
        "Piemonte is the 8th oldest",
        f"{BENCH['verification']['checks']} comparisons",
        f"{BENCH['verification']['numbers']:,} values compared",
        f"takes {fmt_s(rd['seconds'])}",
        f"{rd['rows']:,} rows",
        f"take {fmt_s(ind[1180]['numpy'])} against {fmt_s(ind[1180]['literal'])}",
        f"the whole report {fmt_s(BENCH['report']['seconds'])}",
        f"{min(ratios):.0f} to {max(ratios):.0f} times faster",
        f"(100,000 units: {fmt_s(ind[100000]['numpy'])} against {fmt_s(ind[100000]['literal'])})",
        f"{BENCH['environment']['cpus']} CPUs and Python {BENCH['environment']['python']}",
    ]
    text = flat(README)
    for m in must:
        assert flat(m) in text, m


def test_the_concentration_and_extremes_in_the_text() -> None:
    c = REPORT["concentration"]
    assert c["largest"]["name"] == "Torino" and c["largest"]["population"] == 855_654
    assert (round(c["largest_share"], 1), round(c["top10_share"], 1), round(c["gini"], 3)) == (20.1, 33.5, 0.766)
    assert (c["median_comune_population"], c["under_1000"], round(c["under_1000_population_share"], 1)) == (
        958,
        603,
        6.6,
    )
    ext = REPORT["extremes"]
    assert ext["oldest"][0]["name"] == "Ponzone" and ext["youngest"][0]["name"] == "Bernezzo"
    assert [e["name"] for e in ext["oldest"]] == ["Ponzone", "Ormea", "Portula", "Locana", "Orta San Giulio"]
    assert [e["name"] for e in ext["youngest"]][:2] == ["Bernezzo", "Tarantasca"]
    text = flat(README) + flat(ANALYSIS)
    for s in ("855,654", "20.1%", "33.5%", "0.766", "958 residents", "603", "Ponzone", "744.8", "Bernezzo", "119.9"):
        assert s in text, s


def test_the_analysis_tables_are_the_report() -> None:
    for row in REPORT["provinces"]:
        line = f"| {row['name']} | {row['comuni']} | {round(row['indicators']['population']):,} | {row['indicators']['ageing_index']:.1f} |"
        assert line in ANALYSIS, line
    for s in REPORT["sizes"]:
        assert f"| {s['comuni']} | {s['population']:,} |" in ANALYSIS, s["label"]
    for r in BENCH["indicators"]:
        row = f"| {r['units']:,} | {fmt_s(r['numpy'])} | {fmt_s(r['literal'])} | {r['literal'] / r['numpy']:.0f}x |"
        assert row in ANALYSIS, row
    rd = BENCH["reading"]
    assert fmt_s(rd[0]["seconds"]) in ANALYSIS and fmt_s(rd[1]["seconds"]) in ANALYSIS
    assert fmt_s(BENCH["report"]["seconds"]) in ANALYSIS


def test_the_indicators_in_the_method_are_the_indicators_of_the_code() -> None:
    from odpiemonte.indicators import INDICATORS

    for name in INDICATORS:
        if name != "population":
            assert f"`{name}`" in METHOD, name
