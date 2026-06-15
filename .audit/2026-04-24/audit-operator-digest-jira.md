# JIRA Draft — reporium-audit operator digest

**Lane:** Audit Operator Digest Hardening
**Date:** 2026-04-24
**Branch:** `claude/feature/KAN-AUDIT-audit-operator-digest`
**Target:** `main`
**Repo:** `reporium-audit`
**Relation:** Sibling of `reporium-audit-hardening` / `audit-autopilot-followon`
(both lanes focus on *what is checked* and *how failures are
grouped*; this lane focuses on *what the operator should do about
them*).

## Summary

The nightly `AUDIT_REPORT.md` today prints a flat Failures list and a
flat Full Results table. At 3am when a GitHub issue fires, an operator
reads something like:

> **forksync stale**: 2 days old

…and has to recall, from memory, *which repo that refers to*, *which
workflow page to open*, and *which runbook covers the class of failure*.
That recall cost is the single largest source of operator latency in
the audit loop.

The hardening lane adds structural grouping (areas, Attention
section). This lane fills the missing half: **each failure should carry
a remediation hint so the operator knows what to click next without
thinking.**

## Scope

Owned files only:

- `reporium_audit/reporter.py` (extend with hints + Next Actions block)
- `tests/test_reporter.py` (pin new behavior)
- `README.md` (document the hints section)

Not touched:

- Any check in `reporium_audit/checks/**` — check *names* are the only
  contract; no check needs to change to pick up a hint.
- Any other repo, Cloud Run / Cloud SQL / CI config.

## Changes

### 1. Remediation hint lookup

New module-level `REMEDIATION_HINTS` table in `reporter.py` maps a
check-name matcher to a short, operator-actionable line:

- `reporium-api /health` → "Check Cloud Run revision health; look at
  most recent deploy-api run in reporium-api Actions."
- `reporium-api /repos`, `/search` → "Likely DB connectivity — check
  Cloud SQL pool + last migration in reporium-api logs."
- `contract: no private/fork repos exposed` → "Private repo leaking
  via /library/full — run forksync visibility audit before anything
  else."
- `contract: no null required fields` → "Enrichment pipeline gap —
  check reporium-ingestion nightly run for skipped rows."
- `reporium-db index.json fresh` → "Nightly Sync workflow in
  reporium-db stalled; re-dispatch or inspect last run log."
- `reporium-db repo count` → "Ingest dropped rows — compare to
  forksync output."
- `<repo> CI` → "Open <repo> Actions tab; latest run has conclusion
  != success."
- `<repo> schedule: <wf>` → "Cron run failed; manual
  workflow_dispatch may be masking it — check the schedule event
  runs specifically."
- `knowledge graph build freshness` → "Nightly Graph Build in
  reporium-ingestion stalled; re-dispatch."
- `knowledge graph DEPENDS_ON > 0` → "Edge-type regression —
  compare to KAN-119 snapshot pattern; inspect latest edge_counts
  row."
- `knowledge graph edge count regression` → "Compare latest run in
  v_edge_count_by_run to previous; look for enrichment change."
- `cloud run candidate tags` → "Stale traffic tag on reporium-api;
  apply deploy.yml cleanup step manually via `gcloud run services
  update-traffic --remove-tags`."
- `leaks: <repo> README` → "README contains a forbidden email or
  secret — rotate the secret if real, then open PR to redact."
- `drift: api vs db repo count` → "Cross-source count delta —
  re-run nightly ingestion; confirm /repos, /library/full,
  index.json converge."

Matching is a pure function of the check name. Unknown checks get
no hint (not a generic "investigate" stub — silence beats noise).

### 2. "Next Actions" block

When there are failures, the report now opens (right after Summary)
with a **Next Actions** section that prints, in severity order, the
top failures with:

- the check name,
- a one-line remediation hint,
- a direct Actions URL when the check name implies a repo
  (`<repo> CI`, `<repo> schedule: <wf>`, `leaks: <repo> README`).

Severity order is FAIL → WARN. Within a status, ordering is stable
(input order) so the report diffs cleanly night to night.

This is **additive** to the existing Failures / Warnings / Full
Results blocks — nothing is removed, so downstream consumers (the
nightly diff, the GitHub Issue creator) keep working.

### 3. Hint column in Full Results table

The Full Results table grows a `Hint` column. Empty for checks we
don't have hints for. Operators skimming the table see at-a-glance
where to click.

### 4. Severity-ordered Failures list

The Failures section is now sorted so the checks with hints (i.e.
the ones we've pre-classified as well-understood) float to the top,
followed by hint-less FAILs so *unknown* failures get treated as the
genuinely-unknown outliers they are — worth extra attention, not
buried.

## Tests

- `test_generate_report_includes_remediation_hint_for_known_check`
- `test_generate_report_omits_hint_for_unknown_check`
- `test_generate_report_next_actions_absent_when_no_failures`
- `test_generate_report_next_actions_links_to_actions_tab_when_inferable`
- `test_generate_report_hint_column_in_full_results`

Existing three tests kept intact.

## Verify

```bash
pip install -e '.[dev]'
pytest -q tests/test_reporter.py
python -m reporium_audit run   # with env vars set
```

## Out of scope / stop conditions

- **Issue-title improvements** (the body of the GitHub issue the
  nightly workflow posts) — that's in `.github/workflows/audit.yml`,
  which this lane would not own.
- **Per-failure Slack / paging integrations** — separate lane.
- **Deep-link to commit SHA for CI failures** — requires passing the
  run URL through from `check_workflows`, which means changing check
  output shape. Out of scope; keeping the check contract
  (`check`/`status`/`detail`) stable.
- **Auto-rerun of stalled schedules** — that's a remediation *action*,
  not a reporting concern.

## Residual blind spots (documented, not fixed here)

- Hints are static strings, not parameterised by the detail body. A
  hint cannot (today) quote the specific revision SHA or run URL of
  the failing run; it points you to the right page. Parameterising
  would require the check contract to carry URLs.
- Unknown checks get no hint. If we add a new check and forget to
  register a hint, the operator gets back to today's experience for
  that one check. Acceptable — a visible gap is better than a bogus
  hint.
- Hint text rots if runbooks / workflow names change. Mitigated by
  using generic "open <repo> Actions" patterns rather than hard URLs.
