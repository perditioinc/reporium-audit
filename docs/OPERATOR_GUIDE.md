# Reporium Audit — Operator Guide

High-signal reference for the on-call operator watching the Reporium
suite. Tied to the checks that actually run in `reporium_audit/checks/`;
update this doc when a check is added, removed, or re-ranked.

If you're reading this because an issue fired, jump to
[Escalation by area](#escalation-by-area).

---

## 1. Where to look

| Artifact | Where | Cadence |
|---|---|---|
| `AUDIT_REPORT.md` on `main` | repo root | rewritten nightly ~08:05 UTC |
| Nightly commit `audit: nightly report YYYY-MM-DD` | `git log main` | daily |
| GitHub Issue `Audit failure YYYY-MM-DD` | [Issues](https://github.com/perditioinc/reporium-audit/issues) | only on red run |
| Workflow run | [Nightly Audit](https://github.com/perditioinc/reporium-audit/actions/workflows/audit.yml) | daily 08:00 UTC cron + dispatch |

A missing nightly commit is itself a signal — if today's commit did not
land by 09:00 UTC, the audit did not run.

## 2. How to read the report

`AUDIT_REPORT.md` is written by `reporium_audit/reporter.py` and has a
deliberate top-down layout:

1. **Summary line** — `✓ N/M checks passed | ✗ X failures | ⚠ Y warnings`
2. **Failures** section — every `FAIL` as a bullet. Start here.
3. **Warnings** section — every `WARN` as a bullet.
4. **Full Results** table — every check, including any `SKIP` rows that
   never reach Failures or Warnings.

`SKIP` is not a failure — it means the check could not run because a
secret (`DATABASE_URL`, `GH_TOKEN`, etc.) is not set on the runner.
A `SKIP` row only appears in the Full Results table; treat repeated
SKIPs on the same check as a coverage gap to fix, not a red signal.

Section grouping by *area* (Schedule / Security / Graph / …) is a
planned reporter upgrade that does not ship in the current
`reporter.py`; this guide groups escalation rules by area regardless,
because the *check name* prefix already tells you the area.

## 3. Run it locally

```bash
export REPORIUM_API_URL=https://reporium-api-573778300586.us-central1.run.app
export GH_TOKEN=...       # a PAT with actions:read on perditioinc/*
export DATABASE_URL=...   # optional — enables knowledge graph checks
python -m reporium_audit run
```

Writes `AUDIT_REPORT.md` in the working directory. Safe to run ad-hoc —
all checks are read-only.

## 4. Escalation by area

Rules are per-area, not per-check, so a new check inherits sensible
defaults. Specific checks override below.

### API — `reporium-api /health`, `/repos`, `/search`
- Any `FAIL` → **page**. User-visible surface.
- Flaky single-night `FAIL` → re-run audit; if green, downgrade to Slack.

### Contract — `contract: no private/fork repos`, null fields
- `FAIL` on private/fork exposure → **P0, security**. Same class as the
  2026-04-16 personal-email leak. Take the offending repo private or
  remove from the index immediately, then investigate how it bypassed
  the filter.
- `FAIL` on required-field nulls → P1 data quality.
- `WARN` on enriched-field nulls → backlog item.

### Graph — `knowledge graph …`
- `FAIL` on build freshness (>25h) → page. Nightly graph build stalled.
  Upstream: `perditioinc/reporium-ingestion`.
- `FAIL` on `DEPENDS_ON > 0` → **P0**. Core graph edge type missing;
  same shape as the 2026-04-14 regression (KAN-119).
- `FAIL` on edge-count regression (>50% drop) → P1. Compare run id
  pairs; often resolves by itself on the next build if it was a partial
  commit.
- `WARN` on edge-count regression (>20% drop) → observe.

### Cloud Run — `cloud run candidate tags`
- `FAIL` → file a ticket against `perditioinc/reporium-api` to rerun
  `deploy.yml`'s tag-cleanup step. Not a page — stale tags do not serve
  user traffic, they just leak surface area. Tracking PR: #436.

### DB — `reporium-db index.json fresh`, `reporium-db repo count`
- `FAIL` on freshness → check the nightly sync workflow in
  `perditioinc/reporium-db` and the Cloud SQL password rotation state.
  Not in this repo's control.
- `FAIL` on repo count → cross-check the live `/repos` endpoint count
  against `reporium-db/index.json` count manually; a >5% delta is
  silent ingestion loss.

### Security — `leaks: …`
- `FAIL` on forbidden email → triage: if it's a new personal address,
  purge + rewrite history (see 2026-04-16 playbook). If a legitimate
  team address on a new domain, add it to `AUDIT_ALLOWED_EMAIL_DOMAINS`.
- `WARN` "README.md not found" → the repo shape changed; verify it
  still belongs in the tracked list (`DEFAULT_REPOS` in `leaks.py`).

### Schedule — `<repo> schedule: <workflow>`
- `FAIL` → the scheduled cron is red. This is distinct from the CI
  area: `CI` reads the *latest* run for the repo (which may be a
  passing manual dispatch); `Schedule` filters by the workflow's
  exact name (e.g. `Nightly Graph Build`, `Data Quality Check`) so
  it surfaces only that specific job's most recent run. Trust
  Schedule over CI when they disagree. Repair the schedule in its
  home repo.

### CI — `<repo> CI`
- `FAIL` → open the run log in the named repo. Often already known to
  whichever lane owns that repo.
- `WARN` "No runs" → the repo was likely archived or renamed. Consider
  removing it from `REPOS` in `workflows.py`.

## 5. Top signals of suite drift

Watch for these across consecutive nights; any one is enough to merit a
closer look:

1. **`knowledge graph edge count regression` FAIL** with DEPENDS_ON at
   or near zero. Matches the 2026-04-14 KG regression signature.
2. **`contract: no private/fork repos exposed` FAIL.** A private repo
   leaked into the public index — security-grade.
3. **Any `leaks: … README` FAIL on a forbidden email.** Live PII
   exposure of the same class as the 2026-04-16 regression.
4. **`<repo> schedule: <workflow> FAIL` while `<repo> CI PASS`** for
   the same repo. The cron is red but a manual dispatch is hiding it
   — exactly the Data Quality Check failure pattern from 2026-04-23.
5. **`SKIP` count grows week-over-week.** Secrets are rotting; the
   audit is losing coverage quietly.
6. **Nightly commit missing entirely.** The audit itself stopped
   running — look at the workflow.

## 6. What this audit does NOT cover (dependencies)

These signals live outside `reporium-audit` by design. Do not try to
fold them in here — file against the named owner instead.

| Blind spot | Owner | Signal to watch there |
|---|---|---|
| Latency / p95 on `/repos`, `/search` | `reporium-api` | Sentry, Cloud Run metrics |
| Cloud SQL password rotation | ops runbook | GCP Secret Manager version history |
| Cloud Run tag cleanup on deploy | `reporium-api` `deploy.yml` (PR #436) | Cloud Run revisions tab |
| Graph-build silent corruption past a NullPool crash | `reporium-ingestion` | job logs + Sentry |
| Secret leaks in non-README files (CODEOWNERS, docs/, ADRs) | org-level gitleaks | — (not yet wired) |
| Sentry error-rate gating | audit CI secrets not provisioned | — |

## 7. Weekly review (Monday, 10 min)

At the start of the week, run through this checklist. The companion
template lives at
`.audit/YYYY-MM-DD/audit-weekly-operator-pack.md` — copy it into the
current dated folder to capture the week's snapshot.

- [ ] Seven nightly commits since last Monday? (Missing commit = audit
      stopped.)
- [ ] Any open `Audit failure …` issue? Each one maps to a row in
      the **Failures** or **Warnings** section of the latest
      `AUDIT_REPORT.md`.
- [ ] `AUDIT_REPORT.md` on `main`: any `✗` row in Failures or `⚠` row
      in Warnings? Walk them top-down using §4 Escalation.
- [ ] Compare repo counts in `reporium-api /repos` vs
      `reporium-db repo count` — a silent >5% delta means ingestion is
      dropping rows even when each surface is individually green.
- [ ] `SKIP` count this week vs last week: growing = rotting secrets.
- [ ] New repos in the suite? Add them to `REPOS` in
      `workflows.py` and `DEFAULT_REPOS` in `leaks.py`.

## 8. When to update this guide

- A new check is added to `reporium_audit/checks/` → add an escalation
  row.
- A check is removed → delete its row.
- A real incident exposes a missed signal → add it to §5 "Top signals".
- A blind spot is closed out in another repo → strike it from §6.
