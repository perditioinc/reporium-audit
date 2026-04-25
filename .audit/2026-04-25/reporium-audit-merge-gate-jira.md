# KAN-AUDIT-MERGE-GATE — reporium-audit docs/support PR merge gate (2026-04-25)

**JIRA fallback** — written because no JIRA tool was available to this lane. If/when JIRA returns, copy the body below into a ticket under epic KAN-AUDIT and link the two PRs.

## Lane scope

Decide whether `reporium-audit#12` and `reporium-audit#11` cover live suite gaps well enough to merge now without re-opening solved work. Docs-only / review lane — no application code edits, no merges, no deploys performed.

## Live state validated 2026-04-25 ~03:10 PDT

- `origin/main` HEAD: `80d5352 audit: nightly report 2026-04-25`
- Open PRs in `perditioinc/reporium-audit`: 2 (`#12`, `#11`). No others.
- Both CLEAN / MERGEABLE. Neither has a status-check rollup (this repo runs no PR CI; nightly is `workflow_dispatch` / cron only).

## PR ledger

### #12 — `feat(audit): harden coverage against live failure modes`
- **Branch:** `claude/feature/KAN-AUDIT-reporium-audit-hardening` → `main`
- **Size:** +1,261 / −35 across 12 files
- **Owned files:** `reporium_audit/__main__.py`, `reporium_audit/checks/{cloud_run_tags.py,knowledge_graph.py,leaks.py,workflows.py}`, `tests/test_*.py` (×4), `README.md`, `.audit/2026-04-24/reporium-audit-hardening-{report,jira}.md`
- **What it actually does:**
  - Wires `knowledge_graph.py` into `__main__` (it existed but was never imported — silent dead check, root cause of why KAN-119 needed a human to spot).
  - Adds build-freshness sub-check (>25 h old → FAIL; SKIP when `DATABASE_URL` absent).
  - Filters `check_scheduled_workflows` by workflow *name* so a green `workflow_dispatch` cannot mask a red `Nightly Graph Build` / `Data Quality Check`.
  - Adds `reporium-ingestion`, `reporium-events`, `reporium-audit` to `REPOS`.
  - New `checks/cloud_run_tags.py` — zero-credential probe of `candidate-*` tags, public-spend-surface tripwire (mirrors the live failure mode in `reporium-api#436`).
  - New `checks/leaks.py` — public README PII scan, catches the 2026-04-16 regression class.
- **Author test plan:** `pytest -q` → 28 passed locally. No CI on PR.
- **Risk surface:** new check modules can produce false-positive FAILs on first nightly run. Author called this out under "Residual blind spots" — none of those blind spots block merge.
- **Decision: MERGE AFTER HUMAN SPOT-CHECK** — substantive code change (≈600 lines of new check logic) and the runner is the source of truth for nightly red/green. Reviewer should: (a) run `pytest -q` once, (b) confirm `cloud_run_tags.py` SKIP path triggers when `gh` is unauthenticated rather than crashing the run, (c) confirm `leaks.py` allowlist covers the ***REDACTED-OPERATOR-EMAIL*** purge already on main.

### #11 — `docs: audit weekly operator pack`
- **Branch:** `claude/feature/KAN-AUDIT-audit-weekly-operator-pack` → `main`
- **Size:** +526 / 0 across 4 files
- **Owned files:** `docs/OPERATOR_GUIDE.md`, `.audit/2026-04-24/audit-weekly-operator-pack{,-jira}.md`, `README.md`
- **What it does:** packages the nightly audit for a weekly-cadence operator. File-disjoint from `#12` (touches `docs/`, `.audit/`, README "For Operators" only).
- **PR body claim vs. reality:** body asserts "every rule ties to a check that already ships in `reporium_audit/checks/`; no new checks proposed." Verified against `origin/main`: the guide §4–§5 describe four behaviors that **do not yet exist on main** and are introduced by #12 — `Cloud Run — cloud run candidate tags` (§4, line 88; #12 adds `checks/cloud_run_tags.py`), `Security — leaks: …` (§4, line 99 + §5 row 4; #12 adds `checks/leaks.py`), `Graph — knowledge graph build freshness >25h` (§4, line 79; #12 wires `knowledge_graph.py` into `__main__` and adds the freshness sub-check), and `Schedule` vs `CI` separation pinned on `event=schedule` (§4, line 110–114 + §5 row 5; #12 adds the workflow-name filter to `check_scheduled_workflows`). On current main, `git show origin/main:reporium_audit/__main__.py | grep -E 'knowledge_graph|cloud_run_tags|leaks'` returns zero matches.
- **Implication:** the operator guide describes the **post-#12** main, not the live main. Merging #11 ahead of (or without) #12 would publish operator escalation rules for checks that are not running. Once #12 is in, #11 becomes accurate as written — the PR body's "ties to a check that already ships" assertion is true for the post-#12 check set, just not the live one.
- **Decision: MERGE AFTER HUMAN SPOT-CHECK** — gate the merge on #12 landing first. Reviewer's spot-check is one minute: confirm `origin/main` contains `cloud_run_tags.py` and `leaks.py` and that `__main__.py` imports `knowledge_graph` before approving. No edit to #11 needed.

## Recommended merge order

1. **#12 first.** It introduces the substantive checks the operator guide already describes.
2. **#11 second.** File-disjoint from #12 (no rebase), but content-dependent: #11's operator guide §4–§5 describe behaviors that #12 adds. Order is not optional — reverse order would publish escalation rules for non-existent checks for one cycle.

If #12 ever stalls, #11 must wait, not ship. Do not split #11 to land the non-#12-dependent sections early — the guide is short and the dependent sections are interleaved with the rest.

## Tiny patch

**None proposed.** No file in either PR needs a fix to be merge-safe.

## Stop conditions honored

- No new branch created by this lane.
- No edits to either PR's owned files.
- No merge or deploy performed.

## Provenance

- `gh pr list --repo perditioinc/reporium-audit --state open` (validated 2026-04-25 ~03:10 PDT) — both PRs CLEAN/MERGEABLE.
- `gh pr view 12/11 --json files,statusCheckRollup,body` — file lists and bodies above.
- `git show origin/claude/feature/KAN-AUDIT-audit-weekly-operator-pack:docs/OPERATOR_GUIDE.md | grep -niE 'candidate|leaks|knowledge graph|schedule'` — confirmed #12-introduced check names appear in the guide.
- `git show origin/main:reporium_audit/__main__.py | grep -E 'knowledge_graph|cloud_run_tags|leaks'` and `git show origin/main:reporium_audit/checks/workflows.py | grep -E 'scheduled_workflows|workflow_name|event.*schedule'` — both zero matches on current main, confirming the guide describes the post-#12 main.
