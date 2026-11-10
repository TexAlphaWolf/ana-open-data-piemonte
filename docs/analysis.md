# Analysis

Source: [`report.json`](report.json) (ISTAT POSAS 2026, resident population by age and sex on 1 January 2026, **an estimate**) and
[`bench.json`](bench.json) (one run in Docker on Linux x86_64 with 12 CPUs, Python 3.14.10, NumPy 2.5.4; medians of 5 runs). The
generated tables are in [`report.md`](report.md); this page reads them.

## 1. Piemonte against Italy

| Indicator | Piemonte | Italy |
|---|---|---|
| median_age | 50.8 | 49.3 |
| share_65_plus | 27.2 | 25.1 |
| share_0_14 | 10.9 | 11.6 |
| ageing_index | 248.3 | 216.3 |
| dependency | 61.6 | 58.1 |
| old_age_dependency | 43.9 | 39.8 |
| turnover | 166.3 | 156.0 |
| working_age_structure | 142.5 | 139.4 |
| sex_ratio | 96.2 | 96.3 |

Piemonte is older than Italy on every age indicator, by 1.5 years of median age. The sex ratio is the same (96.2 males per 100
females against 96.3). The turnover of 166.3 says that for every 100 people about to enter the working-age population (15 to 19)
166 are about to leave it (60 to 64). Among the 20 regions Piemonte is the 8th oldest by ageing index, in the group around Toscana
(251.7) and Marche (245.0); Sardegna (299.7), Liguria (290.2) and Molise (272.4) are the oldest, Trentino-Alto Adige (168.5) and
Campania (168.8) the youngest, with a median age of 47.0 and 46.4.

## 2. The eight provinces

| Province | Municipalities | Residents | Ageing index | Rank of 107 (1 = oldest) |
|---|---|---|---|---|
| Biella | 74 | 168,223 | 324.1 | 3 |
| Verbano-Cusio-Ossola | 74 | 152,677 | 301.5 | 7 |
| Alessandria | 187 | 408,063 | 285.8 | 16 |
| Vercelli | 82 | 166,166 | 268.9 | 25 |
| Asti | 117 | 207,059 | 258.7 | 29 |
| Torino | 312 | 2,204,779 | 246.1 | 41 |
| Novara | 87 | 365,930 | 222.1 | 66 |
| Cuneo | 247 | 582,109 | 212.6 | 75 |

The spread inside the region (212.6 to 324.1) is wider than the gap between Piemonte and Italy (248.3 against 216.3). Biella and
Verbano-Cusio-Ossola are older than any region of Italy; Cuneo is younger than Italy as a whole. Torino, with 51.8% of the
residents of the region, sits at 246.1, almost exactly the regional value.

## 3. Municipalities by size

| Residents | Municipalities | Population | % of Piemonte | Ageing index (pooled) | 10th to 90th percentile |
|---|---|---|---|---|---|
| under 500 | 350 | 95,155 | 2.2 | 374.4 | 229 to 794 |
| 500 to 999 | 253 | 183,849 | 4.3 | 306.3 | 212 to 463 |
| 1,000 to 4,999 | 442 | 956,837 | 22.5 | 254.4 | 192 to 362 |
| 5,000 to 19,999 | 103 | 960,065 | 22.6 | 235.9 | 183 to 316 |
| 20,000 and over | 32 | 2,059,100 | 48.4 | 242.3 | 201 to 295 |

The pooled ageing index falls from 374.4 to 235.9 as size grows, then rises a little for the largest class (242.3). The percentiles
tell the second half of the story: among the municipalities under 500 residents the 10th percentile (229) is just below the
regional value (248.3), and the 90th (794) is more than three times it. The smallest municipalities are old on average and very different
from one another.

## 4. Concentration and extremes

Torino has 855,654 residents (20.1%); the ten largest municipalities hold 33.5%. The Gini coefficient of municipality sizes is 0.766
and the median municipality has 958 residents. 603 municipalities (51%) have fewer than 1,000 residents and hold 6.6% of the
population: half of the administrative units of Piemonte serve one resident in fifteen. 487 municipalities have 30% or more of
their residents aged 65 and over, and 30 have 40% or more.

Among municipalities with at least 1,000 residents the five oldest by ageing index are Ponzone (744.8), Ormea (607.5), Portula
(540.0), Locana (511.7) and Orta San Giulio (484.1); the five youngest Bernezzo (119.9), Tarantasca (121.7), Biandrate (127.2),
Beinette (133.9) and Castelletto Stura (134.4). The oldest ones have 1,000 to 1,500 residents; the youngest have 1,377 to 4,276. Ribordone (43 residents) and Cervatto (47) have no child aged 0 to 14, so they have no ageing index and
are left out of the rankings.

## 5. The three files agree

The municipalities of each province add up to the province row, the municipalities of Piemonte to the region row (4,255,006) and
the 107 provinces to the 20 regions (58,942,828 residents), equal for every age and sex. A wrong or truncated file would break
at least one of these sums.

## 6. Speed

| What | Result |
|---|---|
| Reading the 8 province files of Piemonte (1,180 units, 120,360 rows, 4.0 MB) | 266.3 ms (451,946 rows per second) |
| Reading the provinces and regions files (127 units, 0.5 MB) | 35.3 ms |
| The whole report from the loaded tables | 10.6 ms |

| Units | NumPy | Literal | Ratio |
|---|---|---|---|
| 1,180 | 3.8 ms | 49.5 ms | 13x |
| 10,000 | 45.8 ms | 388.4 ms | 8x |
| 100,000 | 440.1 ms | 4.00 s | 9x |

Parsing the text dominates: reading takes 266 ms against 3.8 ms for all the indicators of Piemonte. The NumPy version is 8 to 13
times faster than the literal one, and its cost per unit is 3.2 us at 1,180 units and 4.4 us at 100,000. The sizes of 10,000 and
100,000 units are random tables (there are no more real municipalities of Piemonte); they say how the code scales, not anything
about Italy.

## 7. Agreement

53 comparisons (the three real tables and 50 random ones, with empty classes, no children, nobody over 60 and a single resident):
42,991 values compared, largest relative difference 0.00e+00.
