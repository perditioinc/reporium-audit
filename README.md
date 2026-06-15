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

Produces `AUDIT_REPORT.md` with:

- **Summary** — pass / fail / warning counts.
- **Next Actions** — the on-call-operator's cheat sheet. Every failure
  (and warning) gets a remediation hint and, when the check names a
  repo, a direct link to its GitHub Actions tab. Well-understood
  failures come first so they can be cleared fast; failures we don't
  yet have a hint for appear last, without a hint, so genuinely novel
  issues stand out rather than blend in.
- **Failures / Warnings** — the flat list, kept for backwards
  compatibility with downstream consumers (nightly diff, issue
  creator).
- **Full Results** table — every check, with a `Hint` column that is
  empty unless the check has a registered remediation hint.

Hint coverage is defined in `reporium_audit.reporter.REMEDIATION_HINTS`
and is derived purely from check names — no check has to emit extra
metadata for its failure to get a hint.

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
