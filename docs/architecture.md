# Architecture

```
   cli.py ─────────────────────────────────────────────┐
     │                                                  │
     ▼                                                  ▼
  data.py ──► load.py            analysis.py ──► report.py     verify.py, bench.py
  (folder,    (reader,           (report dict)   (Markdown,    (two implementations,
   hashes)     Table)                             figures)      timings)
                 │                    │
                 └──────┬─────────────┘
                        ▼
             indicators.py (NumPy)   reference.py (literal)
```

| Module | Role |
|---|---|
| `load.py` | The strict reader of a POSAS file into a `Table` (`counts[unit, sex, age]`), and `DataError` |
| `data.py` | Where the files are (option, `$ODP_DATA`, `data/istat`), the Piemonte provinces, `load_dataset`, the hash check |
| `indicators.py` | The 12 indicators for all units at once with NumPy |
| `reference.py` | The same indicators for one unit with plain loops, written to be obviously right |
| `analysis.py` | The report: Piemonte against Italy, provinces, regions, size classes, concentration, extremes, and the reconciliation |
| `verify.py` | Real and random tables, and the comparison of the two implementations |
| `report.py` | Markdown and figures from a report or a benchmark dictionary |
| `bench.py` | Timings of reading and of the indicators |
| `cli.py` | The command line |

## Decisions

- **Only NumPy and matplotlib.** The data has no geometry, so there is nothing for GeoPandas to do, and the tables are small enough
  that pandas would only add a dependency. The counts are one int64 array.
- **The files are kept as published.** They are in the repository byte for byte (`.gitattributes` turns off line-ending
  conversion for `data/`), with a hash manifest, so the analysis can be reproduced from a checkout.
- **A strict reader.** A malformed file is an error that names the line, never a silent repair. The three levels must add up.
- **Integers until the last step.** Counts are int64 and indicators are the only floats, so the two implementations differ only if
  one of them is wrong.
- **The report is rebuilt from its JSON.** `odp render` produces the Markdown and the figure from `report.json` or `bench.json`
  alone, and a test checks that the files in `docs/` are exactly that render.
- **No network, no service.** The program reads files and writes files; the Docker image runs without network, with a read-only
  root and no capabilities.
