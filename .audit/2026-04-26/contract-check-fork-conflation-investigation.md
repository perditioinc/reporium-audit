# Audit/privacy contract investigation — 2026-04-26

**Lane:** investigate the audit/privacy "contract failure" hinted at as a live `/repos` (actually `/library/full`) issue.
**Status:** investigation complete; no PR opened from this lane (lane scope is "investigate", and the operator may want to bundle the two fixes differently).

## TL;DR

- **No actual privacy violation.** Live `/library/full` returns 0 `isPrivate=true` repos out of 200.
- **The "audit/privacy contract failure" is two stacked bugs in `reporium-audit`, neither in `reporium-api`:**
  1. **Audit can't run at all** — `psycopg2` import error (issue [#13](https://github.com/perditioinc/reporium-audit/issues/13), already documented in the +8h log).
  2. **Contract check is misdefined** — [`reporium_audit/checks/contract.py:37`](../../reporium_audit/checks/contract.py:37) flags `isFork OR isPrivate` as a privacy violation. Reporium's curated catalog is forks of upstream open-source repos — that's the product. Once #13 is fixed, this check will FAIL on every clean nightly.

## Live probe results (2026-04-26 ~02:58 PDT / 09:58 UTC)

```
GET https://reporium-api-573778300586.us-central1.run.app/library/full
HTTP=200  TIME=1.0s  SIZE=9.8MB
```

| Field | Value |
|---|---|
| `totalRepos` | 200 (single page returned) |
| `isPrivate=true` count | **0** |
| `isFork=true` count | **200** |
| BOTH `isFork && isPrivate` | 0 |
| Per `contract.py:37` logic | **200/200 = 100% violations** (would FAIL) |

First 5 fork names (sanity check — these are well-known upstream repos, not anything sensitive):
`build-your-own-x`, `awesome`, `freeCodeCamp`, `public-apis`, `free-programming-books`.

## Where the bug originated

```
fe9e5621 (perditioinc 2026-03-22 17:33:56 -0700 37)  private = [repo["name"] for repo in repos if repo.get("isFork") or repo.get("isPrivate")]
fe9e5621 (perditioinc 2026-03-22 17:33:56 -0700 39)  "check": "contract: no private/fork repos exposed",
fe9e5621 (perditioinc 2026-03-22 17:33:56 -0700 41)  "detail": f"{len(repos)} repos, {len(private)} private/fork" if private else f"{len(repos)} public owned repos",
```

Commit `fe9e562` from 2026-03-22 introduced the conflation. The detail string `"public owned repos"` suggests the author expected `/library/full` to be an originals-only surface — but the live response shows it has always been a fork-curation surface (or was at least so before the audit ran). The check has been latently wrong for ~5 weeks because the audit hasn't completed cleanly to surface it.

## Why this matters in the broader sweep

The user's framing "the audit failure may indicate a live contract problem on `/repos`" is correct in spirit but the failure surface is **inside the audit's check definition**, not inside the API's response. Specifically:

- `/library/full` is **NOT** leaking private repos (privacy is intact).
- The audit's notion of "what `/library/full` should return" is **stale / wrong**.

This means: **once #13 is fixed and the audit runs cleanly, the operator will get a false-positive privacy alarm** unless `contract.py:37` is also fixed. The two fixes are coupled in practice.

## Two recommended fixes (both inside `reporium-audit`, both small)

### Fix A — Unblock the audit (issue #13)
Per the +8h log's recommendation (option 2):
- Move `import psycopg2` from module-top of `reporium_audit/checks/knowledge_graph.py` line 24 into the body of `check_knowledge_graph()` (or guard with `try/except ImportError`).
- Preserves the skip-when-`DATABASE_URL`-missing contract that the rest of the file already implements.
- One file changed, ~5 lines.

### Fix B — Stop conflating fork with private
In [`reporium_audit/checks/contract.py:37`](../../reporium_audit/checks/contract.py:37):

```python
# Before
private = [repo["name"] for repo in repos if repo.get("isFork") or repo.get("isPrivate")]
results.append({
    "check": "contract: no private/fork repos exposed",
    ...
    "detail": f"{len(repos)} repos, {len(private)} private/fork" if private else f"{len(repos)} public owned repos",
})

# After
private = [repo["name"] for repo in repos if repo.get("isPrivate")]
results.append({
    "check": "contract: no private repos exposed",
    "status": "PASS" if len(private) == 0 else "FAIL",
    "detail": f"{len(repos)} repos, {len(private)} private" if private else f"{len(repos)} public repos",
})
```

If the operator genuinely *also* wants a "no forks exposed" check on a different surface (e.g., a future `/library/owned`), that's a separate check on a separate endpoint, not this one. Don't reintroduce the conflation under a renamed banner.

Optional add-on: a regression test fixture that verifies `check_contract` does NOT flag `isFork=true` rows (only `isPrivate=true`). Lives in `tests/test_contract.py`.

## What is explicitly NOT a finding

- ❌ `/library/full` exposing private repos — verified false (0 of 200).
- ❌ A `reporium-api`-side bug — the API behavior is consistent with product intent (forks are the catalog).
- ❌ A `reporium-ingestion#67` issue — unrelated; #67 is empty-fork enrichment for the DQ gate denominator.

## Decision on item 4 of the lane plan ("decide whether #67 needs to move")

The audit/privacy investigation does not produce evidence that bumps `#67`'s priority either way. `#67` lives on the DQ enrichment lane, not the audit lane. Its urgency depends on what the +6h post-merge verification of `reporium-api#444` shows about residual `primary_category_coverage` after the column-sync fix + backfill. **Defer the #67 priority decision until after the +6h trigger fires.**

## Exact next action

1. Operator decides which fix lane wants both A and B:
   - Bundle as one PR (`fix(audit): unblock nightly + stop conflating fork with private`) — coupled in practice anyway.
   - OR two PRs in order (A first to unblock, B second to prevent false positive).
2. After landing the fix(es), `gh workflow run audit.yml --repo perditioinc/reporium-audit` to seed the missed 2026-04-26 row and verify both:
   - the audit completes (no psycopg2 crash)
   - `contract: no private repos exposed` returns PASS, not FAIL
3. The +6h scheduled agent (`trig_015qAx1pTpYxfgSCZdqQW9i3`) is independent and continues to track the DQ #444 lane.
