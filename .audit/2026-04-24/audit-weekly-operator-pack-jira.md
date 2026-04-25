# JIRA Draft — reporium-audit weekly operator pack

**Lane:** Audit Weekly Operator Pack
**Date:** 2026-04-24
**Branch:** `claude/feature/KAN-AUDIT-audit-weekly-operator-pack`
**Target:** `main`
**Repo:** `reporium-audit`
**Depends on:** `claude/feature/KAN-AUDIT-reporium-audit-hardening`
(this lane does not modify hardening-lane code, only documents the
shape it lands in)

## Summary

After tonight's hardening lane the audit covers scheduled workflows,
knowledge-graph edges (with build-freshness gating), Cloud Run
candidate tags, and public-README emails. None of that is packaged for
a weekly-cadence operator. A new person going on-call Monday has only
a short README and a flat nightly report — no guide for which `FAIL`
means "page", which means "ticket", which means "re-run tomorrow".

This lane adds a concise, check-tied operator pack: an in-repo
[`docs/OPERATOR_GUIDE.md`](../../docs/OPERATOR_GUIDE.md) and a dated
weekly memo at
`.audit/2026-04-24/audit-weekly-operator-pack.md` that doubles as a
template for future Mondays.

## Scope

Owned files only:

- `docs/OPERATOR_GUIDE.md` (new — in-repo operator guide)
- `README.md` (one appended section pointing at the guide)
- `.audit/2026-04-24/audit-weekly-operator-pack.md` (weekly memo +
  template)
- `.audit/2026-04-24/audit-weekly-operator-pack-jira.md` (this file)

Not touched:

- `reporium_audit/**` — no code change; existing checks are accurate
  as-written.
- `tests/**` — docs-only PR.
- `.github/workflows/**` — cron and issue creation are already correct.
- Any other repo or any live infra.

## Changes

### 1. `docs/OPERATOR_GUIDE.md`

Organized by what an operator does, not by how the code is structured:

- **§1 Where to look** — `AUDIT_REPORT.md`, nightly commit, failure
  issue, workflow page.
- **§2 How to read the report** — Summary line, Failures, Warnings,
  Full Results table, SKIP semantics. Notes that area-grouped output
  is a planned reporter upgrade; this guide groups escalation rules
  by area conceptually, using the check-name prefix as the cue.
- **§3 Run it locally** — env vars + command.
- **§4 Escalation by area** — per-area rules with specific check-name
  overrides (e.g. `FAIL` on `DEPENDS_ON > 0` is a P0, `FAIL` on Cloud
  Run tag is a ticket, not a page). Every rule maps to a check that
  ships today.
- **§5 Top signals of suite drift** — six signals in priority order,
  each anchored to a real incident or a specific check name.
- **§6 What this audit does NOT cover** — table of blind spots, each
  with a named owner outside `reporium-audit`.
- **§7 Weekly review** — 6-item checklist for Monday morning.
- **§8 When to update this guide** — keeps the doc from rotting.

### 2. `README.md`

Adds a "For Operators" section (below the existing "Nightly Schedule")
that points at the operator guide and the weekly pack template. No
existing content removed.

### 3. `.audit/2026-04-24/audit-weekly-operator-pack.md`

Dated weekly memo carrying:

- What to run / monitor (with expected cadence).
- Expected nightly outputs (commit shape, summary-line shape,
  SKIP semantics).
- Escalation table (quick reference; full version in the in-repo guide
  to avoid divergence between the two docs).
- Top signals of suite drift (shared list with guide; this copy
  carries the "as of 2026-04-24" snapshot).
- Monitoring blind spots with owners.
- **Week in review template** — fill-in tables for nightly trail,
  SKIP delta, escalations fired, suite changes.
- Stop conditions — the pack is deliberately NOT a generic SRE
  playbook and NOT a proposal to add more checks.

The file is structured so the next week's operator can copy it to
`.audit/<monday>/audit-weekly-operator-pack.md`, fill the
week-in-review tables, and end up with a week-by-week archive in the
repo.

## Tests

Docs-only PR. No test changes.

Manual verification performed:

- All check names referenced in escalation rules and top-signals
  sections exist in `reporium_audit/checks/` after the hardening
  lane lands:
  - `reporium-api /health`, `/repos`, `/search` (`api.py`)
  - `contract: no private/fork repos exposed` and nulls
    (`contract.py`)
  - `knowledge graph edge counts`, `knowledge graph build freshness`,
    `knowledge graph DEPENDS_ON > 0`, `knowledge graph edge count
    regression` (`knowledge_graph.py`)
  - `cloud run candidate tags` (`cloud_run_tags.py`)
  - `leaks: <repo> README` (forbidden-email scan in `leaks.py`)
  - `<repo> CI` (`workflows.py`)
  - `<repo> schedule: <workflow>` (`workflows.py::check_scheduled_workflows`)

## Out of scope / stop conditions

- **New checks.** If a signal needs its own check, it belongs in a
  hardening or follow-on lane, not here. The pack documents the blind
  spot with a named owner instead (§6 of the guide, "Monitoring blind
  spots" in the memo).
- **Workflow changes.** `audit.yml` already creates the failure issue
  and commits the report. Wiring `if: always()` on the commit step
  (documented in the hardening lane's residual blind spots) is
  explicitly deferred — that is a workflow-lane concern.
- **Auto-generated weekly report.** Considered; deliberately deferred.
  If the manual Monday template becomes heavy it should be turned into
  a check (e.g. a `weekly_digest.py` that consumes the commit trail),
  which is a code lane, not a docs lane.
- **Cross-repo runbooks.** The memo names owners for Cloud Run tags,
  Cloud SQL rotation, graph builds, etc., but does not try to absorb
  their runbooks. Those belong in the owning repos.

## Residual blind spots (documented, not fixed here)

- **No machine-readable digest.** The weekly pack is markdown; an
  operator still has to read the nightly commits to fill the template.
  A follow-on lane could add a `python -m reporium_audit weekly-digest`
  subcommand that reads `git log --grep='^audit: nightly report'` and
  prints the table pre-filled.
- **No per-check severity metadata.** Severity today lives only in
  docs; a future refactor could let each check declare its own
  severity so the reporter (and ticketing integration) pick it up
  automatically. Out of scope — would touch every check file.
- **No alert-routing integration.** "Page" vs "Slack" vs "ticket" is
  documented in prose; there is no PagerDuty / Slack webhook wired.
  That's an ops concern, not an audit-repo concern.

## Verify

```bash
# Docs-only — no test runs required for this PR.
# Quick sanity: confirm the guide's check references still resolve.
grep -Eo '`[a-z_]+\.py`' docs/OPERATOR_GUIDE.md | sort -u
ls reporium_audit/checks/
```
