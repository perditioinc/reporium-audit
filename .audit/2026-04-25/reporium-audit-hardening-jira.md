# Reporium Audit Hardening — 2026-04-25 Validation Pass

**Lane:** `reporium-audit` validation & merge recommendation
**Date:** 2026-04-25
**Author:** Claude Code (validation pass on top of 2026-04-24 in-flight work)
**Status:** No new code change required. Recommendation: ship #12 then #11.

---

## TL;DR

The 2026-04-24 hardening work landed in PR #12 (code) covers the
live failure modes correctly and is merge-ready. PR #11 (operator
docs) has a **dangling-reference defect**: its `OPERATOR_GUIDE.md`
documents a `Drift` area and `secret-pattern` security checks that
only exist in a **local-only commit** (`2eebcc1`) which has never
been pushed to origin. PR #11 must not merge until that orphan
either lands as its own PR or the dangling sections are stripped.

| PR  | Title                                                | State    | Recommendation                  |
|-----|------------------------------------------------------|----------|---------------------------------|
| #12 | feat(audit): harden coverage against live failure modes | MERGEABLE / CLEAN | **GO — merge first** |
| #11 | docs: audit weekly operator pack                     | MERGEABLE but defective | **NO-GO as-is** — see §Orphan-checks defect |

---

## What was validated

1. **Live `main` nightly (`AUDIT_REPORT.md` @ `80d5352`).**
   16 checks total, last commit `audit: nightly report 2026-04-25`.
   The `reporium-api CI` row reads `Keep Cloud Run warm: success` —
   exactly the dispatch-mask failure mode `check_scheduled_workflows`
   is built to expose. Confirms the gap PR #12 closes is real.

2. **PR #12 branch tests.**
   `python -m pytest -q` → **28 passed in 2.08s**.

3. **Code coverage map** — PR #12 against the five live gaps in the
   lane brief:

   | Live gap                                            | PR #12 mechanism                                                                                                       | Covered? |
   |-----------------------------------------------------|------------------------------------------------------------------------------------------------------------------------|----------|
   | Stale public candidate tags                         | `checks/cloud_run_tags.py` — harvests `candidate-*` from deploy runs, probes `<tag>---<host>/health`, compares revision | ✅ Full |
   | Graph freshness stalls / failed graph-build        | `knowledge_graph.py` wired into `__main__` + 25h freshness FAIL + `Nightly Graph Build` in `SCHEDULED_WORKFLOWS`        | ✅ Full |
   | Data-quality plumbing regressions                   | `Data Quality Check` in `SCHEDULED_WORKFLOWS` — filters by workflow name, no longer masked by passing dispatch          | ✅ At workflow layer |
   | Public spend-surface regressions                    | `cloud_run_tags.py` covers stale-tag drift (the recurrent regression class)                                            | ✅ For tag drift; broader compute/egress out of scope |
   | Superseded / red-PR hygiene around critical fixes  | —                                                                                                                       | ❌ Out of scope (see §Residual) |

4. **Cross-PR dependency on PR #12.**
   `docs/OPERATOR_GUIDE.md` (PR #11) references `leaks.py`,
   `DEFAULT_REPOS`, `scheduled_workflow`, and `Data Quality Check` —
   all introduced by PR #12. PR #11 must therefore land **after**
   PR #12 or its operator guide documents non-existent code.

5. **Orphan-checks defect in PR #11 (NEW FINDING).**
   `docs/OPERATOR_GUIDE.md` ships escalation rules for two areas
   whose code lives only in an unpushed local commit (`2eebcc1
   feat(audit): add suite-drift and README secret-pattern checks`):

   | Section in guide | Referenced check | On origin? |
   |------------------|------------------|------------|
   | §4 Drift — `drift: api vs db repo count`, `AUDIT_DRIFT_FAIL_PCT` | `reporium_audit/checks/drift.py` | **No** — local-only on the operator-pack branch |
   | §4 Security — `secret-pattern match (github-token, google-api-key, aws-access-key, slack-token, private-key-pem)` | `reporium_audit/checks/secrets.py` | **No** — same orphan commit |
   | §2 Area banner `Drift ✗` | `reporter.py::AREA_RULES` mapping for "drift" | depends on a check that doesn't exist on origin |

   The guide's own test plan ("every check name referenced in
   `OPERATOR_GUIDE.md` §4–5 exists in `reporium_audit/checks/`
   today") fails against `origin/main` even after PR #12 lands.

   The orphan commit (`2eebcc1`) adds 740 lines of real code:
   `checks/drift.py` (164), `checks/secrets.py` (165), test_drift
   (115), test_secrets (138), plus a JIRA draft. It just needs to
   be pushed and opened as its own PR.

6. **README conflict.**
   Both PRs append after the `Nightly Schedule` section. After #12
   merges, #11 will need a trivial rebase (one append-after-append
   conflict). No semantic conflict.

---

## Merge recommendation

### Order
1. **Merge PR #12 first** (`claude/feature/KAN-AUDIT-reporium-audit-hardening` → `main`).
2. **Resolve PR #11 orphan-checks defect** by either:
   - **Option A (preferred):** push the local commit `2eebcc1` as a
     small follow-on PR (drift.py + secrets.py + their tests) and
     merge it before #11. Wires the operator guide to real code.
   - **Option B:** strip the §4 Drift block, the §4 Security
     `secret-pattern match` bullet, the §2 banner mention of
     `Drift ✗`, and §5 signal-1 from `docs/OPERATOR_GUIDE.md` so the
     doc reflects only what's on `origin/main` after #12.
3. **Rebase PR #11** onto new `main` (resolve the trailing-README conflict).
4. **Merge PR #11** (`claude/feature/KAN-AUDIT-audit-weekly-operator-pack` → `main`).

### Pre-merge gates for #12 — GO
- [x] `pytest -q` green on the head branch (28 passed).
- [x] Diff is confined to owned scope (`reporium_audit/**`,
      `tests/**`, `README.md`, `.audit/2026-04-24/**`).
- [x] No conflict against `origin/main` HEAD (`80d5352`).
- [ ] **Post-merge:** verify the next nightly report on `main`
      contains rows from each new check (`scheduled workflows`,
      `cloud run candidate tags`, `leaks: …`, and either
      `knowledge graph build freshness` PASS/FAIL or a `SKIP` if
      `DATABASE_URL` is unset on the runner).

### Pre-merge gates for #11 — NO-GO until orphan resolved
- [ ] Either push `2eebcc1` (Option A) or strip dangling sections
      (Option B) per §Orphan-checks defect.
- [ ] Rebase onto post-#12 `main`.
- [ ] Spot-check that every check name in `docs/OPERATOR_GUIDE.md`
      §4–5 resolves to a function in `reporium_audit/checks/` after
      the rebase (PR #11's own test plan — currently fails for
      `drift` and `secret-pattern match`).

---

## Why no new patch this lane

The brief's task is "patch only inside `reporium-audit` if there is a
real missing check or reporting gap." The live-gap audit shows:

- Gaps 1–4 are fully addressed by PR #12 as-shipped.
- Gap 5 (red-PR / superseded-PR hygiene) is genuinely missing from
  audit coverage, but it is **PR-queue / coordination state**, not
  runtime suite state. The right home is the dispatch-sheet / lane-13
  release-certification process (already tracked separately), not a
  nightly that reports on `main`. Adding a "PR queue health" check to
  `reporium_audit` would expand the audit's contract from
  "is the live suite healthy?" to "is the merge queue healthy?" —
  out of scope for this lane and a step toward dual-purpose drift.
- The blind spots PR #12 itself documents (Cloud Run tags outside
  the deploy-runs window, secret scans beyond READMEs, workflow-file
  red-run handling) all explicitly belong to follow-on lanes.

Net: no code change required this lane. Validation only.

---

## Residual audit blind spots (after #12 + #11 land)

Captured here for visibility; **not** action items for this lane.

1. **PR-queue / supersession hygiene.** No nightly check correlates
   open PRs touching the same files (e.g., the PR #441 vs PR #435
   NullPool pattern). Owner: dispatch-sheet / release-certification
   process, not `reporium-audit`.
2. **Cloud Run tags outside the recent-deploy-runs window.** PR #12
   probes only tags it can name from recent runs. Authoritative
   enumeration needs GCP credentials. Owner: deploy-side cleanup in
   `reporium-api` (referenced as PR #436 in #12 body).
3. **Silent graph-build corruption that writes zero rows.** Caught
   only when `DEPENDS_ON > 0` plus the regression delta have a
   healthy baseline. A `min absolute count per edge type` floor
   could be added later; not urgent given freshness now FAILs at 25h.
4. **Secret-leak scanning beyond top-level READMEs.** CODEOWNERS,
   `docs/`, ADRs are not scanned. Owner: a future org-level gitleaks
   lane.
5. **Cloud-Run-warm-cron masking pattern, generalized.** PR #12 hard-
   codes four `(repo, workflow_name)` pairs. A more thorough version
   would either (a) auto-discover scheduled workflows from each repo's
   `.github/workflows/` or (b) maintain a pinned schedule manifest. Not
   blocking — current four are the ones we've actually been burned by.
6. **Workflow-file `if: failure()` red-nightly handling.** The
   nightly currently rewrites `AUDIT_REPORT.md` whether or not the
   suite is red. A workflow-file follow-on lane should decide whether
   a red run still commits the report or only opens the issue.

---

## Notes on lane discipline

- One lane, one branch per existing PR. No new branch created.
- No edits outside `reporium-audit`.
- No merge or deploy executed.
- This file is the only artifact added by the validation pass.

JIRA: deferred to operator (JIRA unavailable from this lane). This
file substitutes per process rule #4.
