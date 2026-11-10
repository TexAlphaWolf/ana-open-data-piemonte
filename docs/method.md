# Method

## The files

ISTAT publishes POSAS (*popolazione residente per età, sesso e stato civile*) as CSV files, one row per unit and age. `odp` reads the
files for the age and sex tables only. A file has:

- a title line, `"Popolazione residente per età e sesso al 1° gennaio 2026 (stima)"` (the year and the word *stima* are read from
  it: the 2026 files are an estimate);
- the header `"Codice comune";"Comune";"Età";"Totale maschi";"Totale femmine";"Totale"` (the first two names are `Codice provincia`,
  `Provincia` or `Codice regione`, `Regione` at the other levels), separated by `;` and in UTF-8 with a byte order mark;
- 102 rows per unit: ages 0 to 100 (100 means 100 and over) and `999` for the total of all ages;
- some `Nota:` lines at the end, which are skipped.

The reader groups rows by code, not by position (the national file interleaves two municipalities called Castro) and refuses the
file, with the line, when:

- the title or the exact header is not as expected;
- a code has the wrong width (municipality 6 digits, province 3, region 2);
- a value is not an integer, or males plus females is not the total;
- an age is outside 0 to 100 or appears twice, or an age between 0 and 100 or `999` is missing for a unit;
- the `999` row is not the sum of the 101 ages;
- the same code has two different names.

The result is a `Table` with `counts[unit, sex, age]` as int64, with sex 0 male and 1 female.

## Reconciliation

`reconcile` checks, and raises `DataError` if any is false, that:

1. for each province of Piemonte the sum of its municipalities equals the province row, by age and sex;
2. the sum of the Piemonte municipalities equals the region row `01`;
3. the sum of the 107 provinces equals the sum of the 20 regions, by age and sex.

`odp check-data` also compares the files with `data/SHA256SUMS`.

## Indicators

Bands are inclusive ages; `a..b` counts the residents of both sexes aged a to b. All ratios are per 100, and a ratio with a zero
denominator is NaN (`null` in the JSON).

| Name | Definition |
|---|---|
| `share_0_14` | residents 0..14 as a percentage of all |
| `share_15_64` | residents 15..64 as a percentage of all |
| `share_65_plus` | residents 65..100 as a percentage of all |
| `share_85_plus` | residents 85..100 as a percentage of all |
| `ageing_index` | (65..100) / (0..14), *indice di vecchiaia* |
| `dependency` | ((0..14) + (65..100)) / (15..64), *indice di dipendenza strutturale* |
| `old_age_dependency` | (65..100) / (15..64), *indice di dipendenza degli anziani* |
| `turnover` | (60..64) / (15..19), *indice di ricambio della popolazione attiva* |
| `working_age_structure` | (40..64) / (15..39), *indice di struttura della popolazione attiva* |
| `sex_ratio` | males per 100 females |
| `median_age` | see below |
| `mean_age` | the mean of the ages with each single year counted at its middle (a + 0.5) |

**Median age.** With `n` residents, find the age `a` where the cumulative count first reaches `n/2`, and with `below` the residents
younger than `a` the median is `a + (n/2 - below) / count(a)`: the residents of a single year are taken as evenly spread over it.
Age 100 is "100 and over" and is counted at 100.

## Size classes and the 1,000 rule

Municipalities are grouped by residents into under 500, 500 to 999, 1,000 to 4,999, 5,000 to 19,999 and 20,000 and over. The
indicator of a class is the **pooled** one (the age counts of its municipalities added, then the indicator), which weights by
people; the 10th and 90th percentile are over the municipalities. Rankings of the oldest and youngest municipalities consider only
those with at least 1,000 residents (`MIN_POPULATION`), because below that one family changes the index by tens of points.

## Concentration

The Gini coefficient is the usual one over the 1,180 municipality sizes (0 all equal, near 1 one holds everything); the shares are
shares of the 4,255,006 residents.

## Two implementations

`indicators.py` is vectorised over all units. `reference.py` takes the 101 male and 101 female counts of one unit and computes
every indicator with plain loops and integer sums. `odp verify` compares them with a relative tolerance of 1e-12 (NaNs must be
in the same places) on the real tables and on random tables with awkward cases: empty classes, no children, nobody over 60, one
resident. On the real data the difference is exactly 0.
