# reporium-audit

![License: MIT](https://img.shields.io/badge/license-MIT-brightgreen)

<!-- perditio-badges-start -->
[![Audit](https://github.com/perditioinc/reporium-audit/actions/workflows/audit.yml/badge.svg)](https://github.com/perditioinc/reporium-audit/actions/workflows/audit.yml)
![Last Commit](https://img.shields.io/github/last-commit/perditioinc/reporium-audit)
![python](https://img.shields.io/badge/python-3.11%2B-3776ab)
![suite](https://img.shields.io/badge/suite-Reporium-6e40c9)
<!-- perditio-badges-end -->

> Nightly automated audit of the entire Reporium platform. Single source of truth for platform health.

## What It Checks

- **reporium-api** — `/health`, `/repos`, `/search` endpoints responding.
- **reporium-db** — `index.json` freshness and repo count.
- **Repo CI (latest run)** — pass/fail across the tracked suite
  (`forksync`, `reporium-db`, `reporium-dataset`, `portfolio`,
  `reporium-roadmap`, `reporium-metrics`, `repo-intelligence`,
  `reporium-api`, `reporium-ingestion`, `reporium-events`,
  `reporium-audit`).
- **Scheduled workflows** — per-workflow health for jobs a repo-level
  "latest run" can hide (Nightly Fork Sync, Nightly Sync, Nightly
  Graph Build, Data Quality Check). Catches the failure mode where
  a passing `workflow_dispatch` masks a red cron.
- **Knowledge graph** — edge-count regressions (`DEPENDS_ON > 0`,
  >20%/>50% drops per edge type) and build freshness (latest run
  within 25h) via `v_edge_count_by_run`. Skipped with a note when
  `DATABASE_URL` isn't provisioned rather than silently dead.
- **Cloud Run candidate tags** — harvests `candidate-*` tag names from
  recent `reporium-api` deploy runs and probes the tagged Cloud Run
  URL; flags any tag whose `/health` revision differs from
  production's. Detects the public-spend-surface regression where a
  failed deploy leaves a stale `candidate-*` tag live. Zero GCP
  credentials required.
- **Public README PII leaks** — scans a curated set of public repo
  READMEs for any email outside the allowlisted domains. Catches the
  kind of regression that forced the 2026-04-16 email purge.

## Usage

```bash
export REPORIUM_API_URL=https://reporium-api-573778300586.us-central1.run.app
export GH_TOKEN=...
export DATABASE_URL=...                          # optional; KG check SKIPs without it
export AUDIT_ALLOWED_EMAIL_DOMAINS=example.com   # optional; extends the leak allowlist
python -m reporium_audit run
```

Produces `AUDIT_REPORT.md`. A `SKIP` status in the Full Results table
means the check couldn't run (usually a missing credential) rather
than passed — the gap is made visible rather than hidden.

## Nightly Schedule

Runs at 8am UTC daily (after all other nightly jobs complete). Creates a GitHub issue on any failure.

## What This Audit Does NOT Cover

- **GCP-native surfaces** requiring admin credentials (Cloud Run tag
  enumeration, Cloud SQL replica lag, Pub/Sub DLQ depth). The
  Cloud Run tag check here is a credential-free fallback; full
  enumeration stays manual.
- **Commit history** for leaks — only the current `README.md` on
  `main`/`master` is scanned.
- **Graph-build re-triggering** — the audit observes the graph's
  freshness but does not restart a stalled build; that lives in
  `reporium-ingestion`.

See [`.audit/2026-04-24/reporium-audit-hardening-report.md`](.audit/2026-04-24/reporium-audit-hardening-report.md)
for the most recent coverage expansion and residual blind spots.

## For Operators

On-call? Start here:

- [docs/OPERATOR_GUIDE.md](docs/OPERATOR_GUIDE.md) — how to read the
  report, per-area escalation rules, top signals of suite drift, and
  what this audit does *not* cover (infra/ops dependencies).
- [`AUDIT_REPORT.md`](AUDIT_REPORT.md) on `main` is rewritten nightly;
  a missing daily commit means the audit did not run.
- Weekly review template:
  `.audit/YYYY-MM-DD/audit-weekly-operator-pack.md`.
