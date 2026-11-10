# Security

## Model

odp is a command line program that **reads CSV files and writes a few files**. It starts no service, opens no network connection
and runs no code from its input.

- **What it reads:** the ISTAT CSV files (strictly parsed; a file that is not as expected is refused), the hash manifest, and a
  `report.json` or `bench.json` given to `render`.
- **What it writes:** only where the options say: `report --out`, `bench --out` and `render -o` and `--figure`.
- **The Docker image** runs as an unprivileged user and works with a read-only root filesystem (plus `--tmpfs /tmp` for matplotlib's
  cache), no capabilities and no network (`--network none`); see `tools/docker_e2e.sh`.
- **No personal data.** The files are aggregate counts by municipality, age and sex, published as open data.

## Reporting

If you find a vulnerability, please open a private security advisory on the GitHub repository (Security tab) rather than a public
issue.
