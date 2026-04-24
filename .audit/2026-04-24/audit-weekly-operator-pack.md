# Reporium Audit — Weekly Operator Pack (2026-04-24)

**Lane:** Audit Weekly Operator Pack
**Branch:** `claude/feature/KAN-AUDIT-audit-weekly-operator-pack`
**PR target:** `main` (reporium-audit)
**Companion doc (in-repo):** [`docs/OPERATOR_GUIDE.md`](../../docs/OPERATOR_GUIDE.md)

After nine hours of audit-suite hardening this session, the audit covers
more surfaces than it did in March but nothing packages the new coverage
for a weekly-cadence operator. This pack closes that gap. Keep it
practical — every rule here ties to a check that actually runs.

Copy this file to `.audit/<next-monday>/audit-weekly-operator-pack.md`
each week, fill in the **Week in review** tables at the bottom from the
nightly commit trail, and file issues for the escalations that fired.

---

## What to run / monitor

| When | What | Where |
|---|---|---|
| Every morning | Skim latest `AUDIT_REPORT.md` on `main` | repo root |
| Daily ~09:00 UTC | Confirm a `audit: nightly report YYYY-MM-DD` commit landed | `git log main --since=yesterday` |
| On failure issue fires | Open Attention section first, not Full Results | nightly `AUDIT_REPORT.md` |
| Weekly (Monday, ~10 min) | Walk §"Week in review" template below | this file |
| Ad-hoc | `python -m reporium_audit run` locally | anywhere with env vars |

Required env for a full local run:

```bash
export REPORIUM_API_URL=https://reporium-api-573778300586.us-central1.run.app
export GH_TOKEN=...       # actions:read on perditioinc/*
export DATABASE_URL=...   # enables graph checks (optional)
```

## Expected outputs

- Exactly one nightly commit per day at ~08:05 UTC by `perditio-bot`.
- `AUDIT_REPORT.md` header summary reads `✓ N/M checks passed` with
  no `✗` in the area banner.
- Area banner, stable ordering:
  `API | Contract | Drift | Graph | Cloud Run | DB | Security |
  Schedule | CI` (some may be absent if no checks mapped to them).
- No `## Attention` section — `Attention` only renders when there is a
  FAIL.
- `SKIP` rows only on checks whose secret is not provisioned for the
  nightly runner (currently: `knowledge graph edge counts` if
  `DATABASE_URL` is not wired to CI; `cloud run candidate tags` if
  `GH_TOKEN` is absent).

Anything outside the expected shape is itself a signal — notably a
missing nightly commit.

## Escalation rules

Full per-check table lives in
[`docs/OPERATOR_GUIDE.md` §4](../../docs/OPERATOR_GUIDE.md). Quick
reference:

| Area | FAIL response | WARN response |
|---|---|---|
| **Security** (`leaks: *`) on secret pattern | **P0, rotate credential, purge history** | n/a |
| **Contract** `no private/fork repos exposed` | **P0**, pull repo from index, investigate bypass | — |
| **Graph** `DEPENDS_ON > 0` | **P0**, core edges missing (see KAN-119 postmortem) | — |
| **API** `/health`, `/repos`, `/search` | **Page** — user-visible | Re-run audit |
| **Graph** build freshness (>25h) | **Page** — `reporium-ingestion` nightly stalled | — |
| **Drift** `api vs db repo count` | **P1** silent ingestion loss | Observe 2 nights |
| **Graph** edge count regression (>50%) | P1 | P1 if >20% (WARN-level) |
| **Contract** required-field nulls | P1 data quality | Enriched-null → backlog |
| **Schedule** `<repo>: <workflow>` red | Repair cron in home repo (NOT here) | — |
| **CI** latest run red | Open run in home repo | `No runs` → check if repo archived |
| **DB** index.json freshness | Upstream: `reporium-db` nightly sync | Cross-check Drift |
| **Cloud Run** candidate tags | File ticket on `reporium-api` deploy.yml (PR #436) | — |

Disagreement rule: when `Schedule ✗` and `CI ✓` for the same repo,
trust Schedule. The latest-run check can be hidden by a passing manual
dispatch. This was the Data Quality Check failure pattern on
2026-04-23.

## Top signals of suite drift

In priority order. Any one is enough to dig further.

1. **`Drift` area flips PASS → WARN → FAIL across 2+ nights.** Three
   independently populated surfaces (`api:/repos`,
   `api:/library/full`, `db:index.json`) are diverging. Silent
   ingestion loss is the canonical cause.
2. **`knowledge graph edge count regression` FAIL or
   `DEPENDS_ON=0`.** Matches the 2026-04-14 KG regression signature.
   DEPENDS_ON at zero means the core join is gone, not just slow.
3. **`contract: no private/fork repos exposed` FAIL.** A private or
   fork repo reached the public `/library/full`. Same severity class
   as the 2026-04-16 email-leak incident.
4. **Any `leaks: … README secrets` FAIL.** A credential matched a
   high-confidence pattern. This is already-exposed — rotate first,
   clean git history second.
5. **`Schedule ✗` with `CI ✓` on the same repo.** The cron is red;
   a manual dispatch is masking it in the older "latest run" view.
6. **Growing `SKIP` count week-over-week.** Secrets expiring or
   rotating without the audit runner being updated. Coverage is
   rotting quietly.
7. **Missing nightly commit.** The audit itself stopped.

## Monitoring blind spots (open)

Documented, not fixed here. Each has a named owner outside
`reporium-audit`.

| Blind spot | Owner / next action |
|---|---|
| Latency / p95 regression on `/repos`, `/search` | `reporium-api` — Sentry + Cloud Run metrics; could become a budget-based audit check in a follow-on lane |
| Cloud Run tags created outside recent deploy-run window | `reporium-api` `deploy.yml` (PR #436) — full enumeration requires GCP admin creds not provisioned to CI |
| Graph-build silent corruption past a NullPool crash | `reporium-ingestion` — freshness + DEPENDS_ON catch most, a "green run that wrote zero rows" still needs a baseline |
| Secrets leak in non-README files (CODEOWNERS, docs/, ADRs, workflow files) | Org-level gitleaks, not this repo — would add too much churn per commit |
| Sentry error-rate gating | DSN/API key not provisioned to audit CI |
| Cloud SQL password rotation hygiene | ops runbook; audit can only observe downstream freshness |
| No weekly roll-up auto-generated | This pack is the manual substitute — if it gets heavy, turn it into a check |
| `reporium-events`, `reporium-ingestion`, `reporium-audit` CI surface | Added to tracked list by the hardening lane; verify a first green run appears before treating absence as a real WARN |

## Stop conditions (what this pack deliberately does NOT do)

- Does not propose adding checks — new checks belong in the hardening /
  follow-on lanes which own `reporium_audit/checks/`.
- Does not document generic SRE playbooks. Every rule above maps to a
  check name that ships in this repo today.
- Does not cross into `reporium-api`, `reporium-db`,
  `reporium-ingestion`, or ops runbooks — those are named as owners,
  not absorbed into this pack.

## Week in review — template

Fill this in Monday morning before the standup.

### Nightly commit trail

| Night | Commit landed | Area banner | Issue fired |
|---|---|---|---|
| Mon | y / n | `API ✓ …` | # |
| Tue | | | |
| Wed | | | |
| Thu | | | |
| Fri | | | |
| Sat | | | |
| Sun | | | |

### SKIP count delta

| This week | Last week | Δ |
|---|---|---|
| _n_ | _n_ | _± n_ |

A positive delta is the flag — it means audit coverage regressed.

### Escalations fired this week

| Area | Check | Severity | Ticket |
|---|---|---|---|
| | | | |

### New checks / repos in the suite

| Change | Repo | Needs audit-side update? |
|---|---|---|
| | | |

## References

- In-repo: [`docs/OPERATOR_GUIDE.md`](../../docs/OPERATOR_GUIDE.md)
- Hardening lane: `.audit/2026-04-24/reporium-audit-hardening-report.md`
- Follow-on lane: `.audit/2026-04-24/audit-autopilot-followon-jira.md`
- Workflow: `.github/workflows/audit.yml`
- Reporter layout: `reporium_audit/reporter.py`
