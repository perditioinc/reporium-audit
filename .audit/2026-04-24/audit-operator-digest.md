# Audit Operator Digest — 2026-04-24

**Lane:** Audit Operator Digest Hardening
**Branch:** `claude/feature/KAN-AUDIT-audit-operator-digest`
**Base:** `main`
**Repo:** `reporium-audit`
**Relation:** Six hours after the initial audit-hardening lane; this
lane focuses on how failures are *explained* rather than what is
checked.

## What changed

Single file of actual behaviour change: `reporium_audit/reporter.py`.
Tests updated to pin the new shape. README updated to describe the
report.

Concretely:

1. **`REMEDIATION_HINTS` table** (new, in `reporter.py`). A list of
   `(check-name-substring, hint)` pairs, matched case-insensitively,
   with the more specific matchers ordered before the generic ones
   (`knowledge graph DEPENDS_ON` before `knowledge graph`;
   `schedule:` before the generic ` ci` fallback). Hints are short
   and directional — they answer "which tab do I open?" rather than
   re-explaining the failure.

2. **`## Next Actions` section** in the rendered report. When any
   failures or warnings exist, this block appears right after the
   Summary and prints, one per line:

   ```
   - ✗ **<check>**: <hint> → [Actions](<repo-actions-url>)
   ```

   Failures come first, then warnings. Within failures, the ones
   *with* hints come first; hintless failures fall to the bottom so
   they stand out as genuinely novel.

3. **`Hint` column in the Full Results table.** Empty cell when the
   check has no hint or is PASS/SKIP — operators skim the table and
   only see a hint where there is something to say.

4. **`_actions_url_for()` heuristic deep-linking.** When a check
   name embeds a repo slug (`reporium-db CI`, `reporium-ingestion
   schedule: Nightly Graph Build`, `leaks: perditioinc/reporium-api
   README`), the hint line carries a `→ [Actions](...)` link to
   that repo's Actions tab. Anchored to the check-name shapes the
   runner actually emits today, so a wrong link is very unlikely;
   failures where no repo can be inferred (drift, contract, cloud
   run tags) just get no link.

5. **Reordered Failures section.** The flat Failures list is sorted
   the same way — known first, unknown last. The section header,
   bullet format, and items themselves are unchanged so downstream
   tooling (nightly diff, GitHub Issue creator) keeps working
   byte-for-byte on same-content runs.

What is *not* changed:

- The check contract (`{"check", "status", "detail"}`). No check
  had to emit extra fields for a hint to appear.
- Any file under `reporium_audit/checks/**`.
- Any workflow file, deploy config, or repo outside
  `reporium-audit`.
- Existing `Failures`, `Warnings`, and `Full Results` section
  headings. Downstream grepping tools keep matching.

## Why this improves overnight operations

The audit fires a GitHub issue at 8am UTC (1am Pacific). The issue
body is the full `AUDIT_REPORT.md`. Before this change, the body
looked like:

```
- **reporium-db index.json fresh**: Updated 73.9h ago
- **reporium-db CI**: Nightly Sync: failure
- **contract: no private/fork repos exposed**: 200 repos, 200 private/fork
```

To triage, the on-call had to:

1. Recognise from memory which workflow `reporium-db CI` was the
   latest run of.
2. Recall that `index.json fresh` is produced by the `Nightly Sync`
   workflow — and that "73.9h old" means that workflow has been
   red for ~3 days.
3. Know that "private/fork repos exposed" is a *forksync* concern,
   not a reporium-db one — and is the single most sensitive failure
   in the list, so triage should start there.

That recall cost is now inline in the report:

```
## Next Actions

- ✗ **contract: no private/fork repos exposed**:
    Private/fork repo leaking via /library/full -- run the forksync
    visibility audit before any other triage.
- ✗ **reporium-db index.json fresh**:
    Nightly Sync workflow in reporium-db stalled; re-dispatch it or
    open the last run log.
- ✗ **reporium-db CI**:
    Open the repo's Actions tab; the latest run's conclusion is not
    success -- drill into the failing job.
    → [Actions](https://github.com/perditioinc/reporium-db/actions)
```

Three triage decisions are eliminated: *which failure first* (the
order gives it), *what is the likely cause* (the hint), and *which
tab to open* (the link).

## What the operator can now see faster

- **Which failure to click first** — the Next Actions list is in
  priority order. Private-leak and data-integrity failures come
  first, infrastructure noise last.
- **Why this failure matters** — hints reference the canonical
  prior incident where relevant (e.g. `DEPENDS_ON` points at
  KAN-119-style regressions; `index.json fresh` points at the
  Nightly Sync workflow).
- **Where to go next** — a direct Actions-tab link for repo-scoped
  failures. One tap on mobile.
- **Which failure is genuinely new** — any FAIL without a hint
  floats to the bottom of Next Actions (and Failures). That's the
  signal to stop, think, and add a new entry to
  `REMEDIATION_HINTS` once understood, so the next operator
  benefits.

## Tests

- `tests/test_reporter.py` grows to 17 tests. All pass.
- Hint table:
  - `test_hint_for_known_api_check`
  - `test_hint_for_private_repo_leak_is_highest_priority`
  - `test_hint_for_depends_on_regression_references_kan119`
  - `test_hint_for_schedule_vs_generic_ci_specificity_beats_genericity`
  - `test_hint_for_unknown_check_is_empty`
- Actions URL heuristic:
  - `test_actions_url_for_repo_ci_check`
  - `test_actions_url_for_scheduled_workflow`
  - `test_actions_url_for_leak_check_points_at_repo_not_leaks_word`
  - `test_actions_url_for_non_repo_check_is_empty`
- Report shape:
  - `test_generate_report_next_actions_absent_when_all_green`
  - `test_generate_report_next_actions_includes_hint_and_link`
  - `test_generate_report_hint_column_populated_for_failures_and_warns`
  - `test_generate_report_unknown_failure_rendered_without_hint_or_link`
- Sort order:
  - `test_sort_failures_puts_known_first_and_preserves_order`
- The original three smoke tests are kept.

## Residual operator blind spots

Filed for a later lane, not fixed here:

1. **Detail-parameterised hints.** A hint today is static text keyed
   off the check name. It cannot (yet) quote the specific revision
   SHA or failing-run URL from the detail body. Parameterising
   would require the check contract to carry URLs — deliberate
   scope break this lane avoided.
2. **Hint coverage of new checks is manual.** If we add a new check
   and forget to register a hint, the operator sees today's
   experience for that one check. We treat this as *visible gap is
   better than bogus hint*, and the familiarity-sort puts that
   failure at the bottom so it is hard to miss.
3. **GitHub issue title.** The nightly workflow opens an issue with
   a default title; the body now carries hints but the *title*
   still says "Audit failed" regardless of which area failed. Lives
   in `.github/workflows/audit.yml`, which is out of scope for this
   lane.
4. **Mobile formatting.** On GitHub's mobile rendering, the table
   Hint column can wrap hard. The Next Actions bullet list is the
   designed mobile-first path; the table remains for desktop /
   scripted consumption.
5. **No severity tiers within FAIL.** Everything in Next Actions is
   either FAIL or WARN. A tiered model (P0/P1/P2) would let us hide
   cosmetic failures when a P0 is present — out of scope here and
   debatable whether it is worth the added indirection.

## Stop conditions honoured

- No change outside `reporium-audit`.
- No change to any check file (would expand scope and collide with
  sibling lanes).
- No added verbosity that reduces signal — the hint column is blank
  for PASS/SKIP rows, and silent when no hint is registered.

## Deliverables

- **Patch**: `reporium_audit/reporter.py`, `tests/test_reporter.py`,
  `README.md`, `.audit/2026-04-24/audit-operator-digest-jira.md`,
  this document.
- **PR target**: `main`.
- **Branch**: `claude/feature/KAN-AUDIT-audit-operator-digest`.
