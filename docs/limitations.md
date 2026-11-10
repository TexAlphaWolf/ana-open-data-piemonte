# Limitations

- **An estimate for one date.** POSAS 2026 is ISTAT's estimate of the resident population on 1 January 2026. There is no time
  series here, so nothing says how fast the ageing is going on; the files of other years have the same layout and could be added.
- **Resident population only.** No citizenship, birth place, marital status, households, migration, deaths or births. An old
  municipality may be old because the young left or because the old came; these files cannot tell.
- **Small numbers are noisy.** A municipality of 43 residents has no child (no ageing index) and one of 1,013 has an index of 744.8:
  a few households move these figures. The rankings require 1,000 residents, which is a judgement, not a statistical threshold.
- **Pooled indicators weigh people, percentiles weigh municipalities.** The size-class table shows both so the difference is visible.
- **No geometry, no maps.** Neighbouring municipalities, mountains and valleys are not in the data; the provinces are compared as
  administrative units. Sud Sardegna and other provinces changed in recent years, and the 107 provinces are those of the file.
- **The two implementations share the definition.** They agree exactly, which shows the NumPy code does what the loops do; if the
  definition of an indicator differs from ISTAT's in a detail, both would carry the same error. The definitions are written in
  [`method.md`](method.md) and the median uses interpolation inside the single year, which is one of several conventions.
- **The national municipality file is not included.** It is 27 MB; the benchmark did not time it, and the repository analyses
  Piemonte only.
