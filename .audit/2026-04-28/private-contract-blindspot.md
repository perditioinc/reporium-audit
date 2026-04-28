# Audit private-contract blindspot — Lane 4 closeout

**Branch:** `claude/hotfix/private-contract-blindspot`
**Worktree:** `C:\DEV\PERDITIO_PLATFORM\.worktrees\reporium-audit-private-contract-2026-04-28`
**Base:** `origin/main @ 0400b0b`

## The bug

`reporium_audit/checks/contract.py:40` (pre-fix):

```python
private = [repo["name"] for repo in repos if repo.get("isPrivate")]
```

`dict.get("isPrivate")` returns `None` for any repo whose response payload
doesn't include the field. `None` is falsy, so:

- API emits `isPrivate: true`  → caught (filtered, count > 0, FAIL)
- API emits `isPrivate: false` → public, passes
- API omits the field          → **silently classified as public, passes**

That last branch is what made the audit a no-op for the 2026-04-27
hippo-harvest-assignment incident: the live `/library/full` payload
doesn't emit any privacy field, so every repo trivially passed and the
"contract: no private repos exposed" row read PASS for ~22 hours while
the leak was active. Confirmed:

```
$ curl -sSL https://www.reporium.com/data/library.json | python -c '
import json, sys
d = json.load(sys.stdin)
print("first repo privacy keys:", [k for k in d["repos"][0] if "priv" in k.lower() or "visib" in k.lower()])
'
first repo privacy keys: []
```

## What this PR ships

### Privacy classifier — single source of truth

`_classify_privacy(repo)` returns one of `"public"`, `"private"`, or
`"missing"`. Both naming conventions emitted by reporium-api over time
are recognized:

```python
def _classify_privacy(repo: dict) -> str:
    if repo.get("isPrivate") is True or repo.get("is_private") is True:
        return "private"
    if repo.get("isPrivate") is False or repo.get("is_private") is False:
        return "public"
    return "missing"
```

Missing field = `"missing"`, **never silently downgraded to `"public"`**.

### Two distinct privacy rows per surface

Operators distinguish "API broken / awaiting deploy" from "leak in
production". `_privacy_rows(repos, surface=...)` produces:

| Row | Fails on |
|---|---|
| `<surface>: privacy field present on every repo` | any repo classified `"missing"` |
| `<surface>: no private repos exposed` | any repo classified `"private"` |

Forks are explicitly NOT a privacy violation (the 2026-04-26 conflation
fix is preserved by the test
`test_forks_alone_do_not_trigger_privacy_failure`).

### New surface — static artifact

`check_static_artifact(url)` runs the same two privacy gates against the
baked frontend artifact (e.g. `https://reporium.com/data/library.json`).
The 2026-04-27 incident persisted on the frontend artifact for ~22 hours
*after* the underlying row could be flagged — a stale static artifact is
a separate hop and needs its own gate.

Wired into `__main__.py` alongside the existing checks:

```python
static_artifact_url = os.getenv(
    "REPORIUM_STATIC_LIBRARY_URL",
    "https://reporium.com/data/library.json",
)
...
check_static_artifact(static_artifact_url),
```

`REPORIUM_STATIC_LIBRARY_URL` defaults to production but can be pointed at
a preview / staging artifact host.

## Files touched

| File | Change |
|---|---|
| `reporium_audit/checks/contract.py` | Refactored: `_classify_privacy` helper; `_privacy_rows` produces two rows; new `check_static_artifact(url)` function; both surfaces share gates. |
| `reporium_audit/__main__.py` | Imports `check_static_artifact`; reads `REPORIUM_STATIC_LIBRARY_URL` env var (defaults to prod); adds the new check to the parallel `asyncio.gather` and result aggregation. |
| `tests/test_contract.py` | 13 tests total: 3 pre-existing (kept), 10 new. New tests pin: snake_case `is_private` recognition, mixed-naming, missing field FAILs, partial-missing FAILs, missing-field-doesn't-pretend-private, static-artifact private detection, static-artifact missing-field, static-artifact clean-pass, static-artifact unreachable. |
| `.audit/2026-04-28/private-contract-blindspot.md` | This file. |

## Verification

| Check | Status |
|---|---|
| `pytest tests/test_contract.py -v` | **13 passed**, 2.81s |
| `pytest -q` (full suite) | **41 passed**, 4.61s |
| `ruff check reporium_audit tests` | clean |

### Acceptance check (against the user's task spec)

- ✅ Old hippo-style fixture fails the audit — `test_missing_privacy_field_fails_audit` covers the exact shape (no `isPrivate` field on any repo).
- ✅ Missing privacy field fails the audit — same test plus `test_partial_missing_privacy_field_fails_audit`.
- ✅ Public fork with privacy=false passes — `test_forks_alone_do_not_trigger_privacy_failure`, `test_clean_public_originals_pass`.
- ✅ Tests pass — 41/41.
- ✅ No broad rewrites outside contract/private checks — only `contract.py` and `__main__.py` (2-line wire-up) touched.

### Fork/private separation preserved

The 2026-04-26 fork-conflation fix
(`reporium-audit#14`, commit `d4751ba`) is intact. Test
`test_forks_alone_do_not_trigger_privacy_failure` is unchanged and
passes — `_classify_privacy` only looks at `isPrivate` / `is_private`,
never at `isFork`.

## What this means for the rollout order

The user-stated order remains:

1. Merge/deploy integrated **API** PR (`claude/hotfix/private-leak-integrated-2026-04-28`).
2. Run admin dry-run/apply (mark hippo private + invalidate caches).
3. Merge/deploy **static-artifact** PR (`claude/hotfix/static-private-artifact-2026-04-28`).
4. Regenerate frontend.
5. Verify endpoints + artifact.

This **audit** PR can land before or after the others — its purpose is to
catch the next leak immediately, not to fix this one. **Important:** once
this audit is merged, the next nightly run will FAIL until the API PR is
deployed AND the API exposes `isPrivate` on `/library/full`. That is the
intended behavior.

## Coupling note for the API PR

The integrated API PR (`claude/hotfix/private-leak-integrated-2026-04-28`)
filters private rows via `Repo.is_private == False` but its response
schemas (`app/schemas/repo.py` — `RepoSummary`, `RepoDetail`,
`LibraryFullResponse`) **do not currently expose `isPrivate` or
`is_private` on outgoing repo objects**. The contract here, and the
Lane 2 frontend gate, both require that field to be present in order to
prove leak-freeness.

Until that schema change lands:

- This audit will FAIL on every nightly run with `privacy field present
  on every repo: 1862/1862 missing`.
- Lane 2's `validate-privacy.ts` will FAIL `prebuild` so no new frontend
  build can ship.

The fix on the API side is small — add `is_private: bool` (or
`isPrivate: bool`) to the relevant Pydantic response models so the field
is included in JSON output. Recommend doing this **inside** the existing
integrated API PR rather than as a follow-up, since both Lane 2 and Lane
4 are blocked on it. Add a smoke test in the API repo that asserts the
field is present on a sample `/library/full` response.

## Out of scope (deferred to other lanes)

- **Lane 3** — `reporium-ingestion` RCA (why the row was inserted with
  `is_private=false`). Lane 4 catches the symptom; Lane 3 prevents
  recurrence.
- **Lane 6** — frontend repo-card click regression.

## How to run locally

```bash
cd C:\DEV\PERDITIO_PLATFORM\.worktrees\reporium-audit-private-contract-2026-04-28
python -m pytest tests/test_contract.py -v   # 13 tests
python -m pytest -q                          # 41 tests
python -m ruff check reporium_audit tests    # lint

# Real run against today's production:
export REPORIUM_API_URL=https://reporium-api-573778300586.us-central1.run.app
export GH_TOKEN=<your-token>
python -m reporium_audit run
# expect: privacy-field-present FAIL until API PR deploys
```
