# reporium-audit hardening — coverage report (2026-04-24)

Branch: `claude/feature/KAN-AUDIT-reporium-audit-hardening`
PR target: `main` (reporium-audit)

## What the audit caught **before** this change

From a review of `reporium_audit/**` and the most recent committed
`AUDIT_REPORT.md`:

- `reporium-api` `/health`, `/repos`, `/search` up and serving data.
- `reporium-db` `index.json` repo count + 25h freshness.
- `/library/full` contract: private/fork exposure, null required fields,
  null enriched fields.
- **Latest** GitHub Actions run status per tracked repo.

## What the audit **missed**

Cross-referenced against recent incidents (2026-04-14 KG regression,
2026-04-16 email-leak purge, 2026-04-23 Cloud Run tag cleanup, Data
Quality Check 3x-failing schedule):

1. **Knowledge-graph edge-count regressions.** A dedicated module
   (`checks/knowledge_graph.py`) existed but was **never imported** by
   `__main__`. It was dead code. The April KG regression had to be
   caught by a human because this audit never ran it.
2. **Red schedules hidden by green dispatches.** `check_workflows` only
   reads the latest run of *any* event. A manual `workflow_dispatch`
   success will hide a cron that has failed 3× in a row.
3. **Stale Cloud Run candidate tags** on the public `reporium-api`
   service. No check, no signal.
4. **PII regression in public READMEs** — specifically the personal-
   email class of leak from 2026-04-16. Only the `/library/full`
   private-fork check was defending that surface.
5. **Stale tracked-repo list.** `reporium-ingestion`, `reporium-events`,
   and `reporium-audit` itself were not in `REPOS`, so any failing CI
   run on those repos stayed invisible to the audit.
6. **SKIP semantics.** Previously, a missing secret caused a `FAIL` row
   that looked the same as a real failure. That encourages "just set it
   to some value" workarounds. SKIP is now a first-class status.

## What the audit **now catches**

| New capability | Code | Test |
|---|---|---|
| KG module wired into the runner | [reporium_audit/__main__.py](reporium_audit/__main__.py) | [tests/test_knowledge_graph_wiring.py](tests/test_knowledge_graph_wiring.py) |
| KG build freshness (< 25h) | [reporium_audit/checks/knowledge_graph.py](reporium_audit/checks/knowledge_graph.py) | — (requires live DB) |
| Scheduled-workflow gating by name | [reporium_audit/checks/workflows.py](reporium_audit/checks/workflows.py) | [tests/test_workflows.py](tests/test_workflows.py) |
| Expanded tracked-repo list (ingestion, events, audit) | [reporium_audit/checks/workflows.py](reporium_audit/checks/workflows.py) | [tests/test_workflows.py](tests/test_workflows.py) |
| Cloud Run candidate-tag leak probe | [reporium_audit/checks/cloud_run_tags.py](reporium_audit/checks/cloud_run_tags.py) | [tests/test_cloud_run_tags.py](tests/test_cloud_run_tags.py) |
| Public-README PII leak scan | [reporium_audit/checks/leaks.py](reporium_audit/checks/leaks.py) | [tests/test_leaks.py](tests/test_leaks.py) |
| Reporter `SKIP` status (surfaces gaps) | [reporium_audit/reporter.py](reporium_audit/reporter.py) | [tests/test_reporter.py](tests/test_reporter.py) |

Test suite: **29 passed** locally.

## What still requires manual/operator review

Documented blind spots — *not* fixed here, either because they belong to
another repo or because the audit CI can't reach the signal safely.

1. **Cloud Run tags created outside the recent-deploy-runs window.**
   Full tag enumeration requires GCP credentials that aren't provisioned
   for this CI. The deploy-side fix belongs to [#436](https://github.com/perditioinc/reporium-api/pull/436).
   Our probe catches the common case (tag referenced in a deploy run name)
   and documents the rest.
2. **Graph-build pipeline failures that don't surface as workflow
   failures** (silent corruption past a NullPool crash, partial commits).
   The freshness + DEPENDS_ON + regression checks catch most, but a
   "green run that wrote zero nodes" is only caught by the regression
   delta, which needs a healthy baseline.
3. **Secrets leak in non-README files** — CODEOWNERS, docs/, ADRs,
   workflow files. Could be extended; kept out of scope to avoid
   churn on every legitimate commit.
4. **Workflow-level `failure()` issue creation.** The audit workflow
   uses `if: failure()` but `__main__` does not `sys.exit(1)` on
   failed checks (doing so would skip the `AUDIT_REPORT.md` commit
   step and hide the detail from future readers). Wiring this up
   cleanly requires `if: always()` on the commit step — a workflow
   tweak that belongs in a follow-on lane so the audit repo keeps
   committing reports even on red runs.

## Process notes

- Owned scope respected: edits confined to `reporium_audit/**`,
  `tests/**`, `README.md`, and `.audit/`. No changes to other repos,
  no workflow edits, no deploy.
- `pyproject.toml` deliberately not modified. `psycopg2` stays an
  optional runtime dep; KG check self-skips when missing. If operators
  want live KG checks, they install with `psycopg2-binary` and set
  `DATABASE_URL`.
- Branch `claude/feature/KAN-AUDIT-reporium-audit-hardening` off `main`,
  one PR's worth of change, not merged.
