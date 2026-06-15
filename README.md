# reporium-audit

<!-- perditio-badges-start -->
[![Audit](https://github.com/perditioinc/reporium-audit/actions/workflows/audit.yml/badge.svg)](https://github.com/perditioinc/reporium-audit/actions/workflows/audit.yml)
![Last Commit](https://img.shields.io/github/last-commit/perditioinc/reporium-audit)
![python](https://img.shields.io/badge/python-3.11%2B-3776ab)
![suite](https://img.shields.io/badge/suite-Reporium-6e40c9)
<!-- perditio-badges-end -->

> Nightly automated audit of the entire Reporium platform. Single source of truth for platform health.

## What It Checks

| Check | What it catches |
|-------|-----------------|
| `reporium-api /health`, `/repos`, `/search` | API up and serving real data |
| `contract: /library/full` | No private/fork repos exposed, no null required/enriched fields |
| `reporium-db index.json` | Repo count and 25h freshness |
| `workflows: latest run` | Red CI on any tracked repo |
| `workflows: scheduled` | Red *scheduled* run even when a `workflow_dispatch` is green |
| `cloud run candidate tags` | Stale `candidate-*` traffic tags on `reporium-api` |
| `leaks: README` | Non-allowlisted email addresses in public READMEs |
| `knowledge graph edge counts` | DEPENDS_ON=0, edge-type regressions, build freshness |

### Scheduled-workflow gating

`check_workflows` reports the latest run of any kind, so a manual
`workflow_dispatch` success can mask a broken cron job. `check_scheduled_workflows`
filters on `event=schedule` for a curated list so a red schedule (e.g. `Data Quality
Check`, `Nightly Graph Build`) surfaces immediately.

### Cloud Run candidate-tag probe

Failed deploys can leave `candidate-*` traffic tags pointing at old
revisions of the public `reporium-api` service. We don't have GCP
credentials in audit CI, so the check:

1. Harvests tag names from recent `reporium-api` deploy-workflow runs
   (via `GH_TOKEN`).
2. Probes each tagged Cloud Run URL (`<tag>---<host>/health`).
3. Flags any tag whose revision differs from production's `/health` revision.

Tags created outside the recent-runs window are a documented blind spot
and belong to the post-deploy cleanup step in `reporium-api`'s `deploy.yml`.

### Public-README PII leak

Fetches `README.md` from a curated set of public repos and flags any
email address whose domain is not in the allowlist. Designed to catch
the regression pattern where a personal email address leaks into a
public README.

- Default allowlist: `perditio.com`, `perditioinc.com`, GitHub noreply.
- Override with `AUDIT_ALLOWED_EMAIL_DOMAINS=a.com,b.com`.

### Knowledge-graph checks

Checks three things against the DB's `v_edge_count_by_run` view:

- **Build freshness**: latest run started within 25h.
- **DEPENDS_ON > 0**: the edge type most commonly zeroed by regressions.
- **Edge-type regression**: any type dropping >20% (WARN) or >50% (FAIL) vs the previous run.

Requires `DATABASE_URL` and `psycopg2` (optional dep). SKIP without either.

## Usage

```bash
export REPORIUM_API_URL=https://reporium-api-573778300586.us-central1.run.app
export GH_TOKEN=...
# Optional:
export DATABASE_URL=postgresql://...      # Enables knowledge-graph checks
export AUDIT_ALLOWED_EMAIL_DOMAINS=...    # Extra allowlisted email domains

python -m reporium_audit run
```

Produces `AUDIT_REPORT.md` with a full results table split into
**Failures**, **Warnings**, **Skipped**, and the raw matrix.

## Nightly Schedule

Runs at 8am UTC daily (after all other nightly jobs complete). Creates a
GitHub issue on any failure.

## Development

```bash
pip install -e '.[dev]'
pytest -q
```
