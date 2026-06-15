# JIRA Draft — reporium-audit autopilot follow-on

**Lane:** Audit Autopilot Follow-on
**Date:** 2026-04-24
**Branch:** `claude/feature/KAN-AUDIT-audit-autopilot-followon`
**Target:** `main`
**Repo:** `reporium-audit`
**Depends on:** `claude/feature/KAN-AUDIT-reporium-audit-hardening` (same-night lane)

## Summary

The hardening lane made `reporium-audit` aware of scheduled workflows,
the knowledge graph, Cloud Run tags, and README email leaks. Several
autopilot-meaningful blind spots remain, specifically:

1. Silent **data-volume drift** between the API and the DB is invisible.
   If ingestion quietly drops half the repos, `/repos` still returns a
   number > 0 and `index.json` is still "fresh" — everything stays
   green. This is the class of bug that took a human to catch twice in
   the last month.
2. The README leak scan only looks for **personal emails**. A leaked
   GitHub token, GCP key, or AWS secret would slip through today, even
   though those are strictly worse regressions than the 2026-04-16 email
   incident.
3. The report still reads like a flat checklist. When five things fail
   at once an operator has to eyeball the table to figure out which area
   to look at first.

## Scope

Owned files only:

- `reporium_audit/checks/drift.py` (new)
- `reporium_audit/checks/leaks.py` (extend — adds secret-pattern scan;
  does not change existing email behavior)
- `reporium_audit/__main__.py` (wire drift check)
- `reporium_audit/reporter.py` (group output by area + actionable
  "Attention" summary)
- `tests/test_drift.py` (new)
- `tests/test_leaks_secrets.py` (new — covers the new secret patterns
  without touching the hardening lane's `tests/test_leaks.py`)
- `tests/test_reporter.py` (extend with grouping assertions)
- `README.md`

Not touched:

- Any other repo or Cloud Run / Cloud SQL infra
- Hardening-lane files except via strictly additive edits to
  `__main__.py`, `reporter.py`, `leaks.py`

## Changes

### 1. Cross-source suite drift check (`check_suite_drift`)

New `reporium_audit/checks/drift.py` reconciles three independently
populated counts:

- `reporium-api` `/repos?limit=1` `total`
- `reporium-api` `/library/full` `repos` length
- `reporium-db` `data/index.json` `meta.total`

Emits a **single** drift check that compares pairwise deltas:

- Delta ≤ 2 repos **or** ≤ 1% of the largest source → `PASS`
- Delta between 1% and 5% → `WARN`
- Delta > 5% → `FAIL`

This catches silent loss (ingestion dropped rows, migration cleared a
table, enrichment cache never refilled) that none of the existing
checks would see.

All three sources are already reachable, so no new secrets are
required; thresholds are env-configurable via
`AUDIT_DRIFT_WARN_PCT` / `AUDIT_DRIFT_FAIL_PCT`.

### 2. README secret-pattern scan (extends `check_leaks`)

Adds a companion pass in `leaks.py` that scans the same README bodies
already being fetched (no extra HTTP) for high-confidence leaked-secret
patterns:

- GitHub tokens: `ghp_`, `ghs_`, `gho_`, `github_pat_`
- Google API keys: `AIza...` (39 chars)
- AWS access keys: `AKIA...` (20 chars)
- Slack bot / user tokens: `xoxb-`, `xoxp-`
- PEM private key headers: `-----BEGIN * PRIVATE KEY-----`

Any hit → `FAIL` (we don't WARN on a secret; if it matched the pattern
it's already out). The check returns a **separate** result per repo so
an operator can tell *which* README tripped without reading the table.

Residual blind spots (documented, not fixed):

- Non-README files (CODEOWNERS, docs/, ADRs) — out of scope for this
  lane; belongs in a dedicated git-history scan.
- False positives on literal placeholder text in docs
  (`AKIA...example...`) — mitigated by requiring the full char count
  and boundary anchors, but not eliminated.

### 3. Operator-useful report output

`reporter.py` gains:

- An **"Attention"** section at the top that lists every `FAIL` grouped
  by *area* (API / Contract / DB / CI / Schedule / Graph / Cloud Run /
  Security / Drift / Other), so the operator sees where to look first
  instead of scanning a 30-row table.
- A one-line health banner summarizing area-level status ("API ✓ |
  Schedule ✗ | Graph ✓ | Security ✗").
- Area inference is a pure function of check-name prefix — no check
  needs to be re-labelled.
- Existing Failures / Warnings / Skipped / Full Results sections kept
  intact so downstream tooling (GitHub Issue creator, nightly diff)
  doesn't break.

## Tests

- `tests/test_drift.py` — mocks all three sources; covers PASS /
  WARN / FAIL / partial-source-unreachable paths.
- `tests/test_leaks_secrets.py` — asserts each secret pattern fires,
  asserts legitimate repo text does not, asserts detection is surfaced
  as FAIL even when the email scan would have passed.
- `tests/test_reporter.py` — new cases:
  - Area grouping places a `reporium-api /health` FAIL under "API".
  - "Attention" section omitted when no FAILs are present.
  - Area health banner reflects a FAIL in the right area.

## Verify

```bash
pip install -e '.[dev]'
pytest -q
python -m reporium_audit run   # with env vars set
```

## Out of scope / stop conditions

- **Cloud Run admin API tag enumeration** — still blocked on GCP creds;
  inherited from hardening lane.
- **Git-history / non-README secret scan** — requires cloning each
  repo; too heavy for a nightly runner and large enough to deserve its
  own lane.
- **Sentry / error-rate gating** — depends on DSN + API key not
  provisioned to audit CI. If added later it should be a new check.
- If the drift check turns out to be flaky (e.g. because
  `/library/full` and `index.json` are populated from different windows
  and briefly disagree around midnight), the thresholds above are
  intentionally loose and env-overridable; if still flaky the check
  degrades to WARN rather than being removed.

## Residual blind spots (documented, not fixed here)

- Latency / p95 regression on `/repos` and `/search` (numbers are
  available in the responses; a separate lane should turn them into a
  budget-based check).
- Dead candidate tags created outside the deploy-workflow window
  (inherited from hardening lane).
- Secret leaks in non-README files.
