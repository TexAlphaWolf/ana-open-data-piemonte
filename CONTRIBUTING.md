# Contributing

```bash
pip install -e ".[dev]"
ruff check . && ruff format --check . && mypy && pytest --cov
```

No service is needed. `ODP_TEST_DRAWS` and `ODP_TEST_SEED` run the same tests with more (or different) random tables (CI also uses
150 draws with seed 11).

Rules that keep the project honest:

- **A change to an indicator needs both implementations.** Change `indicators.py` (NumPy) and `reference.py` (literal) the same
  way, update the definition in `docs/method.md`, add a hand-computed case to `tests/test_indicators.py` and let `odp verify`
  compare them.
- **The data files stay as published.** Do not edit anything in `data/istat/`; add a new file with its hash in `data/SHA256SUMS`.
- **A change to the reader keeps it strict.** A new accepted deviation needs a test that says why.
- **Numbers in the README and `docs/analysis.md` come from `docs/report.json` and `docs/bench.json`**, and `tests/test_docs.py`
  checks them. After a change to the analysis, regenerate them (`odp report --out`, then `tools/run_full.ps1` for the benchmark) and
  update the text where a number moved.
