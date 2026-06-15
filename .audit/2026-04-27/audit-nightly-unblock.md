# Audit Nightly Unblock — handoff

**Date:** 2026-04-27
**Lane:** Audit Nightly Unblock (close out the issue-#13 + contract-conflation pair)
**Status:** **code complete on branch + missing-psycopg2 test coverage added** — needs PR + merge.
**Branch:** `fix/audit-contract-fork-conflation`
**HEAD:** `e0edcd1 fix(audit): drop fork conflation and lazy-import psycopg2` plus uncommitted test additions in `tests/test_knowledge_graph_wiring.py` (this lane).

## TL;DR

The two-bug pair the 2026-04-26 investigation flagged ([`contract-check-fork-conflation-investigation.md`](../2026-04-26/contract-check-fork-conflation-investigation.md)) is already fixed on `fix/audit-contract-fork-conflation`:

1. **Issue #13 (psycopg2 import error blocks audit)** — `import psycopg2` moved from module-top of `reporium_audit/checks/knowledge_graph.py` into the body of `check_knowledge_graph()`, guarded with `try/except ImportError`. Lazy import preserves the SKIP-when-`DATABASE_URL`-empty contract.
2. **`isFork OR isPrivate` conflation in `contract.py:37`** — replaced with `isPrivate`-only filter; check name renamed `"contract: no private repos exposed"`; detail strings updated to drop `/fork`.

A regression test fixture was committed alongside (`tests/test_contract.py`):
- `test_forks_alone_do_not_trigger_privacy_failure` — three pure-fork repos return `PASS`.
- `test_private_repo_triggers_failure` — one `isPrivate=true` row produces `FAIL` with `"1 private"` in the detail.
- `test_clean_public_originals_pass` — mixed clean catalog with no private rows returns `PASS`.

**This lane (2026-04-27) added missing-`psycopg2` test coverage** that the original commit did not include. The pre-existing `test_knowledge_graph_skips_when_db_url_missing` only covered the empty-`DATABASE_URL` SKIP path; the runner-survival contract for "missing `psycopg2` does not abort `asyncio.gather`" was not pinned. Two new tests in `tests/test_knowledge_graph_wiring.py` close that gap (see "Tests added by this lane" below).

The lane is now a hygiene closeout: open the PR (now with the additional KG tests), merge to `main`, re-trigger the audit workflow once the merge lands so the missed 2026-04-26 row is filled.

## What's on the branch

```
e0edcd1 fix(audit): drop fork conflation and lazy-import psycopg2
```

`git diff main HEAD` (verified 2026-04-27):

```diff
diff --git a/reporium_audit/checks/contract.py b/reporium_audit/checks/contract.py
@@ -33,12 +33,15 @@ async def check_contract(api_url: str) -> list[dict]:
             data = r.json()
             repos = data.get("repos", [])

-            # Check: no private repos
-            private = [repo["name"] for repo in repos if repo.get("isFork") or repo.get("isPrivate")]
+            # Check: no private repos.
+            # Forks are intentionally part of the curated catalog (Reporium's
+            # product surface is forks of upstream open-source repos), so they
+            # are not a privacy violation. Only ``isPrivate=true`` is.
+            private = [repo["name"] for repo in repos if repo.get("isPrivate")]
             results.append({
-                "check": "contract: no private/fork repos exposed",
+                "check": "contract: no private repos exposed",
                 "status": "PASS" if len(private) == 0 else "FAIL",
-                "detail": f"{len(repos)} repos, {len(private)} private/fork" if private else f"{len(repos)} public owned repos",
+                "detail": f"{len(repos)} repos, {len(private)} private" if private else f"{len(repos)} public repos",
             })

diff --git a/reporium_audit/checks/knowledge_graph.py b/reporium_audit/checks/knowledge_graph.py
@@ -21,8 +21,6 @@ from __future__ import annotations
 from datetime import datetime, timedelta, timezone

-import psycopg2
-

 STALE_RUN_THRESHOLD = timedelta(hours=25)

@@ -46,6 +44,19 @@ async def check_knowledge_graph(db_url: str) -> list[dict]:
         })
         return results

+    # psycopg2 is imported lazily so the SKIP path above doesn't require the
+    # dep. The audit's declared deps are httpx + python-dotenv only; psycopg2
+    # is only needed when DATABASE_URL is set (issue #13).
+    try:
+        import psycopg2
+    except ImportError as e:
+        results.append({
+            "check": "knowledge graph edge counts",
+            "status": "FAIL",
+            "detail": f"psycopg2 not installed: {e}",
+        })
+        return results
+
     try:
         conn = psycopg2.connect(db_url)
```

Plus the new `tests/test_contract.py` (107 lines, three test cases, all parametrized via `respx.mock` against `httpx.AsyncClient`).

## Tests added by this lane (2026-04-27)

`tests/test_knowledge_graph_wiring.py` previously had two tests: one that pins the import wiring into `__main__`, one that covers the empty-`DATABASE_URL` SKIP path. Neither covered the missing-`psycopg2` runtime path. This lane adds two more:

- `test_knowledge_graph_does_not_crash_when_psycopg2_missing` — uses `monkeypatch.setitem(sys.modules, "psycopg2", None)` to force the in-function `import psycopg2` to raise `ModuleNotFoundError`. Asserts the function returns a single result row (status FAIL, detail mentions `"psycopg2"`) and does **not** raise. This is the runner-survival contract — the `asyncio.gather` in `__main__.run_audit` cannot tolerate any check raising.
- `test_knowledge_graph_skip_path_does_not_import_psycopg2` — same monkeypatch, but called with `db_url=""`. Asserts the SKIP path completes without ever needing `psycopg2`, pinning the issue-#13 contract that the audit's declared deps remain `httpx + python-dotenv` only.

The first test's assertion `"psycopg2" in row["detail"]` is RED-discriminating against an unfixed module-top-import scenario:

| Scenario | `row["detail"]` | `"psycopg2" in detail` |
|---|---|---|
| **Fixed (lazy import + missing psycopg2)** | `"psycopg2 not installed: …"` | True (test PASSes) |
| **Unfixed (module-top import, psycopg2 already loaded in test env)** | `"DB error: could not translate host name 'unused-host' to address …"` | False (test FAILs) |

So a future regression that slides the import back to module-top will be caught.

Full local suite after additions: **33 passed, 0 failed** (was 31 before this lane).

```
$ python -m pytest tests/ -v
============================= 33 passed in 2.86s ==============================
```

## Suggested PR body

```
fix(audit): drop fork conflation and lazy-import psycopg2

Bundles two correlated fixes that together unblock the nightly audit:

1. Lazy psycopg2 import (closes #13). The module-top import broke
   `python -m reporium_audit` on every CI runner that hadn't pip-installed
   psycopg2 — which is most of them, since the README declares only httpx
   and python-dotenv as deps. The import is now inside check_knowledge_graph
   and guarded with try/except ImportError, preserving the SKIP-when-
   DATABASE_URL-empty contract.

2. Drop isFork-or-isPrivate conflation in contract.py. Reporium's product
   surface is forks of upstream open-source repos; flagging every fork as
   a privacy violation would FAIL the audit on every clean nightly. The
   check now matches only isPrivate=true. The check name and detail strings
   were updated to drop "/fork" from the user-visible messages.

Why bundled: once #1 lands the audit starts running cleanly, and that
immediately surfaces the conflation as a false-positive privacy alarm.
Shipping them separately would mean a window where the operator sees a
false red. Bundling avoids the window.

Tests added in tests/test_contract.py (respx-mocked httpx):
- test_forks_alone_do_not_trigger_privacy_failure (regression for #2)
- test_private_repo_triggers_failure (genuine privacy still caught)
- test_clean_public_originals_pass (mixed catalog still passes)

Tests added in tests/test_knowledge_graph_wiring.py (2026-04-27 follow-up):
- test_knowledge_graph_does_not_crash_when_psycopg2_missing (runner-survival
  contract — pins that asyncio.gather cannot abort on missing psycopg2)
- test_knowledge_graph_skip_path_does_not_import_psycopg2 (declared-deps
  contract — SKIP path remains psycopg2-free)

Provenance:
- .audit/2026-04-26/contract-check-fork-conflation-investigation.md
- .audit/2026-04-27/audit-nightly-unblock.md (this lane's handoff)

Closes #13.
```

## Operator steps after merge

```sh
# 1. Merge
gh pr merge --squash --repo perditioinc/reporium-audit <PR>

# 2. Trigger the audit so the missed 2026-04-26 nightly row gets filled
gh workflow run audit.yml --repo perditioinc/reporium-audit

# 3. Verify both gates pass on the next run
gh run watch --repo perditioinc/reporium-audit
```

Expected output, reading the workflow log for the `check_contract` and `check_knowledge_graph` rows:

- `contract: no private repos exposed` → **PASS** (200 forks, 0 private)
- `contract: no null required fields` → **PASS** (0 nulls)
- `contract: no null enriched fields` → **PASS** or **WARN** (depends on enrichment coverage; not blocking)
- `knowledge graph build freshness` → **FAIL** today, will flip to **PASS** as soon as the Nightly Graph Build is unblocked (separate lane, R1 in the audit ranking)
- `knowledge graph DEPENDS_ON > 0` → **PASS** (89 edges, per Apr 19 snapshot — this number lives in `v_edge_count_by_run`, not the audit code)

If the contract gate FAILs after this merge, the failure shape is now meaningful — it means there really *is* an `isPrivate=true` row in `/library/full`, and the operator should investigate immediately. Before this merge, the gate was guaranteed to FAIL on every fork-bearing nightly and the signal was useless.

## What this lane does NOT do

- Does not push the branch (`fix/audit-contract-fork-conflation` is already on origin per the 2026-04-26 lane log).
- Does not open the PR — operator action.
- Does not change `knowledge graph build freshness`. That's blocked on Cloud SQL secret rotation in `reporium-ingestion` ops (separate lane, R1 in the audit dashboard).
- Does not address the `enriched fields` `null` rate. The contract check returns `WARN` not `FAIL` on missing enriched fields; that's the right behavior. Populating those fields lives in the queued `source-attestation-enrichment-spec` lane.

## `gh workflow run audit.yml` — was it triggered?

**No.** This lane did not invoke `gh workflow run audit.yml --repo perditioinc/reporium-audit`. Two reasons:

1. **The fix is on the unmerged branch `fix/audit-contract-fork-conflation`.** The scheduled `audit.yml` workflow runs against `main`. Triggering it pre-merge would re-execute the broken `main` code and reproduce the same crash, which gives no signal about whether the fix works.
2. **A workflow run is shared-state.** It writes a row to the workflow history that an operator scanning recent runs could mistake for a clean post-merge result. Cleaner to merge first, then trigger (or wait for the 08:00 UTC scheduled run) so the green/red signal is unambiguous.

The intended sequence remains the one in "Operator steps after merge" above.

## Remaining risk

| Risk | Likelihood | Mitigation |
|---|---|---|
| **Branch isn't merged** — the fix is local-only until a PR opens and merges. The next 08:00 UTC scheduled run on `main` will still crash. | High (today) | Open PR; tests are green so review should be quick. |
| **PR conflicts with `main`** — the branch was last touched 2026-04-26 03:18 PDT plus this lane's test addition; main may have moved. | Low | Standard rebase. The two production files (`contract.py`, `knowledge_graph.py`) are not high-traffic. |
| **First post-merge nightly genuinely surfaces an `isPrivate=true` row** — with the conflation removed, the check is now a true privacy alarm. Any FAIL after merge is no longer noise. | Low (live probe 2026-04-26 showed 0 of 200) | This is the desired contract. Document in PR description so operators don't dismiss the first FAIL as a regression. |
| **CI environment loses `psycopg2`** — the new test pins the runtime degradation, not the CI install step. If CI's dev-deps install drops `psycopg2`, the audit completes but the KG check goes FAIL. | Low | The CI install step lives in `.github/workflows/audit.yml`; this lane did not change it. |
| **Other module-top imports of optional deps** — this lane only fixed `psycopg2`. Any other check that does a module-top `import optional_dep` has the same bug shape. | Unknown — out of scope | A grep across `reporium_audit/checks/*.py` for module-top imports of non-declared deps is a 5-minute follow-up. |
| **`/library/full` schema drift** — the contract check assumes `repo.get("isPrivate")` returns a falsy value for public repos. If the API ever stops emitting `isPrivate` entirely, the check trivially passes. | Low | A separate "schema completeness" check on `/library/full` could pin that the field exists per row; out of scope here. |

## Provenance

- 2026-04-26 contract investigation: `reporium-audit/.audit/2026-04-26/contract-check-fork-conflation-investigation.md`
- Contract source on `fix/audit-contract-fork-conflation` HEAD `e0edcd1`: `reporium_audit/checks/contract.py` (lines 36–46), `reporium_audit/checks/knowledge_graph.py` (lines 47–58)
- Test fixture: `tests/test_contract.py` HEAD `e0edcd1`
- Diff against `main`: verified clean 2026-04-27 via `git diff main HEAD`

---

## Update — 2026-04-27 (Cowork 10h coordinator session — audit-nightly merge watch)

**Anchor:** 2026-04-27 (Pacific morning, several hours after this handoff was filed).
**Lane:** Cowork 10h coordinator session, Workstream D (audit-nightly merge / workflow verification watch).
**Posture:** read-only. No edits to the fix branch, no PR opened, no workflow triggered. Working-tree edits to other `.audit/2026-04-24/*.md` files visible in `git status -sb` are unrelated to this lane and were not touched.

### Branch state — verified locally (read-only)

| Surface | Reading | Verdict |
|---|---|---|
| `main` HEAD (local + origin) | `bfb1366 docs: audit weekly operator pack (#11)` | unchanged since prior to this fix lane |
| `fix/audit-contract-fork-conflation` HEAD (local + origin) | `e0edcd1 fix(audit): drop fork conflation and lazy-import psycopg2` | unchanged from this handoff's stated HEAD |
| Distance | **1 commit ahead of main** | fix not yet merged |
| Local-vs-origin parity on the fix branch | `## fix/audit-contract-fork-conflation...origin/fix/audit-contract-fork-conflation` (no ahead/behind) | tracked, pushed |
| `tests/test_knowledge_graph_wiring.py` working-tree state | clean against HEAD; file contains all 4 tests including `test_knowledge_graph_does_not_crash_when_psycopg2_missing` (line 37) and `test_knowledge_graph_skip_path_does_not_import_psycopg2` (line 53) | the two new tests this handoff names as "added by this lane (2026-04-27)" are committed in `e0edcd1`, not uncommitted |

**Net:** `e0edcd1` is the single, complete fix commit (lazy psycopg2 + contract de-conflation + the four contract tests + the two new wiring tests). It is on the branch, on origin, and **not on `main`**. The handoff's "Status: code complete on branch + missing-psycopg2 test coverage added — needs PR + merge" remains accurate.

### Workflow state — NOT LIVE-VERIFIED

Cowork's sandbox does not have `gh` CLI installed and `apt-get install gh` is blocked (no sudo / no-new-privileges). The handoff's "Operator steps after merge" §3 (`gh run watch`) cannot be exercised by Cowork. The exact `gh` checks the operator should run after merge are unchanged from §"Operator steps after merge"; this Update adds the **pre-merge** check the operator may want first:

```bash
# Pre-merge: is there already an open PR for this branch?
gh pr list --repo perditioinc/reporium-audit \
  --head fix/audit-contract-fork-conflation \
  --state all \
  --json number,state,isDraft,mergeable,baseRefName,statusCheckRollup,reviewDecision

# If no PR exists, open one with the suggested body in §"Suggested PR body":
gh pr create --repo perditioinc/reporium-audit \
  --head fix/audit-contract-fork-conflation --base main \
  --title 'fix(audit): drop fork conflation and lazy-import psycopg2' \
  --body-file <(cat <<'PRBODY'
[paste from §"Suggested PR body" of audit-nightly-unblock.md]
PRBODY
)

# Pre-merge: latest run of audit.yml on origin/main (the broken one).
# Should be a failure ("ImportError: psycopg2") prior to this fix.
gh run list --repo perditioinc/reporium-audit --workflow audit.yml --limit 5 \
  --json databaseId,headBranch,headSha,conclusion,createdAt,event
```

Audit.yml has not been triggered by Cowork (the handoff's §"`gh workflow run audit.yml` — was it triggered?" already explains why pre-merge triggers are not useful). Cowork is not authorized to merge.

### Disposition

- **Blocked: fix branch not merged to `main`.** No code action by Cowork. The next operator action is the §"Suggested PR body" + §"Operator steps after merge" sequence, unchanged from the original handoff.
- The two new wiring tests are committed and pushed; PR description should call them out (the §"Suggested PR body" already does).
- After merge, the operator runs `gh workflow run audit.yml --repo perditioinc/reporium-audit` once on `main` and verifies the run via `gh run watch`. Cowork records the post-merge run id below when/if the operator pastes it; this Update does not pre-fill.

### Cowork did NOT

- open the PR
- merge the branch
- push, rebase, or amend any commit
- trigger `audit.yml` (pre-merge against `main` would re-execute the broken code; post-merge requires merge first — neither is in Cowork's scope)
- modify any file in `reporium_audit/`, `tests/`, `.github/workflows/`, or `pyproject.toml`
- read any secret or print any credential

### Mirror

A copy of this Update is staged at:
`C:\DEV\PERDITIO_PLATFORM\.cowork-2026-04-27\parallel-lanes\audit-nightly-watch.md`
(Lane prompt's intended `parallel-lanes\` path is unmounted in unsupervised Cowork — see `cowork-10h-session-log.md` §"path constraints".)
