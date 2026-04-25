# JIRA Draft — reporium-audit hardening lane (2026-04-25)

**Lane:** Audit Hardening Lane
**Date:** 2026-04-25 (overnight, ~04:00–14:00 PDT window)
**Branch:** `claude/feature/KAN-AUDIT-audit-hardening-lane`
**Target:** `main`
**Repo:** `reporium-audit`
**Sibling lanes:** `KAN-AUDIT-reporium-audit-hardening` (PR #12),
`KAN-AUDIT-audit-weekly-operator-pack` (PR #11)

---

## TL;DR

The 2026-04-24 hardening (PR #12) is merge-ready and the live nightly
on `main` already proves the dispatch-mask gap PR #12 closes is real
(2026-04-25 nightly: `reporium-api CI` row reads
`Keep Cloud Run warm: success`, while the actual `Data Quality Check`
schedule cannot be inferred from that). PR #11's docs were referencing
checks (`drift`, `secret-pattern`) and a reporter shape (area banner,
Attention section) that never shipped to origin — that defect has been
patched on PR #11's branch by stripping the dangling sections rather
than expanding either PR's scope.

This lane wrote no new check code. The improvements are: (a) strip
PR #11 to match what actually ships, (b) document the merge order and
residual blind spots for the morning operator, (c) preserve the
2026-04-25 validation memos on origin so the next lane is not flying
blind.

## Lane scope

- **Owned files:**
  - `.audit/2026-04-25/*.md` (this lane's notes)
  - `docs/OPERATOR_GUIDE.md` (already patched on PR #11's branch)
  - `.audit/2026-04-24/audit-weekly-operator-pack{,-jira}.md` (already
    patched on PR #11's branch)
- **Not touched:**
  - `reporium_audit/**` and `tests/**` — PR #12's code is the source
    of truth; this lane validates and does not modify it.
  - Other repos, workflow files, deploy infrastructure.
- **Not merged or deployed.**

## Live state at lane start (verified 2026-04-25 ~04:00 PDT)

| Surface | State |
|---|---|
| `origin/main` HEAD | `80d5352 audit: nightly report 2026-04-25` |
| Open PRs in `reporium-audit` | 2 (`#11`, `#12`) |
| PR #12 mergeStateStatus | CLEAN, MERGEABLE, 0 reviews, no required CI |
| PR #11 mergeStateStatus | CLEAN, MERGEABLE, 0 reviews, no required CI |
| Latest nightly summary | `✓ 14/16 checks passed \| ✗ 1 failures \| ⚠ 1 warnings` |
| Live FAIL on `main` | `contract: no private/fork repos exposed` (200 / 200) |
| Live WARN on `main` | `perditioinc/repo-intelligence workflows: No runs` |

The `200 repos, 200 private/fork` FAIL on `main` is an in-flight
suite-level signal owned by `reporium-api` (already filed at
[perditioinc/reporium-api#440](https://github.com/perditioinc/reporium-api/pull/440)
class). It validates that the audit's contract check is doing its
job; not a defect of this lane.

## Cross-PR gap audit

Three forms of dangling references were resolved:

### 1. PR #11 OPERATOR_GUIDE referenced unshipped checks

`docs/OPERATOR_GUIDE.md` documented a `Drift` escalation block and a
`secret-pattern match` security bullet that mapped to
`reporium_audit/checks/drift.py` and `secrets.py` — both files exist
only in a local commit `2eebcc163d7d330ddd8c920a350205f4ffc7bff8` that
has never been pushed to origin (sat on the operator-pack branch
locally, not in any PR).

**Patch:** strip the dangling sections from `OPERATOR_GUIDE.md`,
`audit-weekly-operator-pack.md`, and the JIRA draft. PR #11 now
documents only what ships in `reporium_audit/checks/` after PR #12
lands.

### 2. PR #11 OPERATOR_GUIDE referenced unshipped reporter output

§2 "How to read the report" described an area banner
(`API ✓ \| Contract ✓ \| Drift ✗ ...`) and an `## Attention` section.
Neither is in `reporium_audit/reporter.py` on origin, and PR #12 does
not modify `reporter.py`. They live in a stash
(`stash@{0}: operator-pack + hardening WIP`) that never landed.

**Patch:** rewrite §2 to match the live `reporter.py` output
(Summary / Failures / Warnings / Full Results table). Keep §4 organized
by area as a *conceptual* grouping driven by the check-name prefix;
note that area-grouped output is a planned reporter upgrade.

### 3. PR #11 escalation table referenced `event=schedule` filter

§4 Schedule said `Schedule pins on event=schedule`. PR #12's
`check_scheduled_workflows` actually filters by *workflow name*
client-side (the GitHub API's `event=schedule` query parameter is
not the actual mechanism in code).

**Patch:** clarify the filter is by workflow name, matching PR #12's
implementation.

## What is NOT being added in this lane

- **`drift.py` / `secrets.py` and their wiring.** The orphan commit
  `2eebcc1` adds 740 lines of real working code with passing tests.
  Pushing it as a separate follow-on PR is recommended — see
  [reporium-audit-hardening-jira.md](reporium-audit-hardening-jira.md)
  validation memo. Doing so is *not* in this lane's mandate to keep
  scope minimal and avoid expanding PR #12 to slow its merge.
- **`reporter.py` area-banner / Attention upgrade.** Lives in
  `stash@{0}` locally; same logic applies — needs its own PR.
- **PR-queue / supersession hygiene.** A nightly that reports on
  cross-PR file conflicts (PR #441 vs #435 NullPool, PR #436 vs #438
  deploy.yml) is dispatch-process work, not nightly suite-state work.
  Out of audit-repo scope.

## Merge recommendation

1. **PR #12 first.** Adds the substantive checks (KG wiring + freshness,
   scheduled-workflow name filter, Cloud Run candidate-tag probe,
   public-README forbidden-email scan). 28 tests passing locally, no
   conflict against `origin/main`.
2. **PR #11 second.** Trivial README rebase needed (both PRs append
   after the same `Nightly Schedule` section). After the strip
   committed in this lane, PR #11's operator guide describes only
   checks that exist on `main` after #12 lands.
3. **(Optional follow-on)** `drift.py` + `secrets.py` follow-on PR —
   builds on the orphan commit `2eebcc1`, adds `__main__.py` wiring,
   and (optionally) a future reporter upgrade for the area banner.

## Stop conditions honored

- No new branch was strictly required — but one was created
  (`claude/feature/KAN-AUDIT-audit-hardening-lane`) per the lane
  brief's allowance, solely to host the validation memos and morning
  note where they will be visible to the next lane on origin.
- No edits outside `reporium-audit`.
- No merge or deploy executed.
- All edits touched only `docs/`, `.audit/`, and lane-coordination
  files — never `reporium_audit/` or `tests/`.
