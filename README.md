# reporium-audit

<!-- perditio-badges-start -->
[![Audit](https://github.com/perditioinc/reporium-audit/actions/workflows/audit.yml/badge.svg)](https://github.com/perditioinc/reporium-audit/actions/workflows/audit.yml)
![Last Commit](https://img.shields.io/github/last-commit/perditioinc/reporium-audit)
![python](https://img.shields.io/badge/python-3.11%2B-3776ab)
![suite](https://img.shields.io/badge/suite-Reporium-6e40c9)
<!-- perditio-badges-end -->

> Nightly automated audit of the entire Reporium platform. Single source of truth for platform health.

## What It Checks

- reporium-api: /health, /repos, /search endpoints responding
- reporium-db: index.json freshness and repo count
- All GitHub Actions workflows: pass/fail status across 8 repos

## Usage

```bash
export REPORIUM_API_URL=https://reporium-api-573778300586.us-central1.run.app
export GH_TOKEN=...
python -m reporium_audit run
```

Produces `AUDIT_REPORT.md` with full results table.

## Nightly Schedule

Runs at 8am UTC daily (after all other nightly jobs complete). Creates a GitHub issue on any failure.

## For Operators

On-call? Start here:

- [docs/OPERATOR_GUIDE.md](docs/OPERATOR_GUIDE.md) — how to read the
  report, per-area escalation rules, top signals of suite drift, and
  what this audit does *not* cover (infra/ops dependencies).
- [`AUDIT_REPORT.md`](AUDIT_REPORT.md) on `main` is rewritten nightly;
  a missing daily commit means the audit did not run.
- Weekly review template:
  `.audit/YYYY-MM-DD/audit-weekly-operator-pack.md`.
