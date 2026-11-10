# Benchmark

Run on Linux x86_64, 12 CPUs, Python 3.14.10, NumPy 2.5.4; seed 1; each time is the median of 5 runs; command `bench --sizes 10000,100000 --ref-max 100000 --repeat 5 --draws 50 --out /out`.

## 1. Reading the files

| Files | Units | Rows | Size | Time | Rows per second |
|---|---|---|---|---|---|
| Piemonte, 8 province files | 1,180 | 120,360 | 4.0 MB | 266.3 ms | 451,946 |
| all provinces and regions | 127 | 12,954 | 0.5 MB | 35.3 ms | 366,982 |

## 2. The indicators: NumPy against the literal implementation

| Units | NumPy | Literal | Ratio |
|---|---|---|---|
| 1,180 | 3.8 ms | 49.5 ms | 13x |
| 10,000 | 45.8 ms | 388.4 ms | 8x |
| 100,000 | 440.1 ms | 4.00 s | 9x |

## 3. The whole report

Building the report of Piemonte from the loaded tables takes 10.6 ms.

## 4. Agreement

53 comparisons (the three real tables and 50 random ones): 42,991 values compared, the largest relative difference is 0.00e+00. All agree.
