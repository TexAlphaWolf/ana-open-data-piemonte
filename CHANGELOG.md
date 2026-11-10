# Changelog

## 1.0.0

First release.

- A strict reader of the ISTAT POSAS files (population by age and sex) for municipalities, provinces and regions, with the 2026 files
  of Piemonte, the provinces and the regions shipped as published and a hash manifest.
- The 12 ISTAT demographic indicators (ageing index, dependency, old-age dependency, turnover, working-age structure, shares, sex
  ratio, median and mean age) for every unit, with NumPy, and a literal implementation of the same indicators.
- `odp verify`, which compares the two on the real tables and on random awkward ones.
- The analysis of Piemonte: against Italy, the eight provinces among 107, the regions, municipalities by size, concentration,
  extremes among municipalities with at least 1,000 residents, and the reconciliation of the three levels.
- A report (JSON, Markdown, figure) rebuilt exactly from its JSON, and a benchmark of reading speed, indicator speed and agreement.
- A command line with exit codes for a pipeline (0 ok, 1 a hash mismatch or a verification failure, 2 an error).
- Docker image (no network, read-only, no capabilities); CI on Python 3.11 to 3.14, Linux, Windows and macOS.
