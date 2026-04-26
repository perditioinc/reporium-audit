# JIRA Draft — Harden reporium-audit suite

**Lane:** Audit Suite Hardening
**Date:** 2026-04-24
**Branch:** `claude/feature/KAN-AUDIT-reporium-audit-hardening`
**Target:** `main`
**Repo:** `reporium-audit`

## Summary

`reporium-audit` has drifted. The nightly AUDIT_REPORT.md still checks the
same four surfaces it did in March, but the failure modes that have hurt
us recently are different. Examples the current audit would miss or has
already missed:

- Graph edge-count regression was coded but **never wired into the runner**
  (`knowledge_graph.py` is never imported by `__main__.py`). That's why
  KAN-119 and follow-on regressions took a human to catch.
- Scheduled workflows like "Data Quality Check" and "Nightly Graph Build"
  can be red while the *latest* run (the one `check_workflows` reads) is
  a passing `workflow_dispatch` or unrelated CI run. The audit reports
  green while the scheduled jobs fail for days.
- Cloud Run candidate traffic tags from failed deploys accumulate on the
  public service and are invisible to any current check. PR #436 fixes
  the deploy side; the *audit* side has no mirror.
- `contract: no private/fork repos exposed` is the only private-leak
  tripwire. It does not cover the 2026-04-16 regression (personal email
  leaking into a public README), which was only caught by a human.
- The tracked repo list is stale — `reporium-ingestion`, `reporium-events`,
  and `reporium-audit` itself aren't in `REPOS`.

## Scope

Owned files only:

- `reporium_audit/**`
- `tests/**`
- `README.md`

Not touched:

- `deploy.yml` / per-repo workflows (belong to their repos)
- Any other repo

## Changes

### 1. Wire the already-coded knowledge-graph check into the runner

`reporium_audit/checks/knowledge_graph.py` exists but is not imported.
`__main__.py` now imports it, runs it when `DATABASE_URL` is set, and
skips with a documented `SKIP` result otherwise. Added a freshness sub-check
that fails if the latest run's `started_at` is older than 25 hours.

### 2. Workflow-name-aware scheduled-run check

New `check_scheduled_workflows` complements `check_workflows`. For a
curated list `(repo, workflow_name)` it hits
`/repos/{repo}/actions/workflows/{workflow_name}/runs?event=schedule` and
asserts the latest *scheduled* conclusion is `success`. Catches the
Data Quality Check / Nightly Graph Build failure pattern that the
"latest run" check hides.

Expanded tracked repos to include `reporium-ingestion`, `reporium-events`,
and `reporium-audit`.

### 3. Cloud Run candidate-tag leak probe

New `check_cloud_run_tags` does not require GCP credentials. It reads
recent deploy-workflow runs from `reporium-api` (via `GH_TOKEN`) to
harvest candidate tag names, then probes the tagged Cloud Run URL
pattern `https://<tag>---<service>-<hash>.run.app/health`. Any tag that
resolves *and* serves a revision different from production's `/health`
revision is flagged as a stale candidate. Documented limitation: we can
only see tags referenced in recent workflow run names — if a tag was
created outside that window it is invisible from here and belongs to the
`deploy.yml` cleanup step (PR #436).

### 4. Public-README PII leak check

New `check_leaks` fetches raw READMEs for a curated set of public repos
(`reporium-api`, `portfolio`, `reporium-audit`, etc.) and scans them for
forbidden patterns (default: any non-`@perditio.*` email). Catches the
kind of regression that forced the 2026-04-16 email-purge. Patterns are
env-configurable via `AUDIT_FORBIDDEN_EMAIL_DOMAINS`.

### 5. Reporter: SKIP status + grouping

Reporter now understands `SKIP` (for checks that can't run without a
secret — e.g. `DATABASE_URL`) and prints a dedicated Skipped section so
the gap is visible rather than silent.

## Tests

- `tests/test_reporter.py` — existing tests kept; new cases for SKIP.
- `tests/test_workflows.py` — new; mocks GitHub API, verifies scheduled-
  workflow gating.
- `tests/test_leaks.py` — new; mocks README fetches, verifies email
  pattern detection and allowlist.
- `tests/test_cloud_run_tags.py` — new; mocks GitHub + Cloud Run probe
  responses.
- `tests/test_knowledge_graph_wiring.py` — new; verifies `__main__` skips
  gracefully when `DATABASE_URL` is missing.

## Out of scope / stop conditions

- **`deploy.yml` tag cleanup** — belongs in `reporium-api` (PR #436). We
  only *audit* the result, we do not fix the deploy.
- **Cloud Run admin API tag enumeration** — requires GCP credentials not
  present in this CI. The tag-name-via-workflow-logs approach is the
  safest feasible fallback; full enumeration stays as manual/operator
  review.
- **Graph-build trigger** — audit only observes. Re-running the build on
  stall is a `reporium-ingestion` job.

## Verify

```bash
pip install -e '.[dev]'
pytest -q
python -m reporium_audit run   # with env vars set
```

## Residual blind spots (documented, not fixed here)

- Candidate tags created outside the deploy-workflow window.
- Graph build pipeline failures that do not surface as workflow failures
  (e.g. silent data corruption past the NullPool crash).
- Secrets-leak scanning of non-README files (CODEOWNERS, docs/, ADRs).
