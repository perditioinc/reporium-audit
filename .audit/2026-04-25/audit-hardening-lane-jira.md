# Audit Lane — 2026-04-25 Lane Log

## +3h follow-up: 2026-04-25 ~20:05 PDT

**State changed since 17:03 PDT checkpoint — both PRs merged to `main`.**

| PR | Title | Merged at (UTC) | Merged by | Merge commit | Base |
|---|---|---|---|---|---|
| [#12](https://github.com/perditioinc/reporium-audit/pull/12) | feat(audit): harden coverage against live failure modes | 2026-04-26 00:06:50 | kimmymakesmoves | `1002030` | main |
| [#11](https://github.com/perditioinc/reporium-audit/pull/11) | docs: audit weekly operator pack | 2026-04-26 00:29:07 | kimmymakesmoves | `bfb1366` | main |

`origin/main` HEAD advanced `80d5352` → `1002030` → `bfb1366`. Merge order matches the dependency the docs PR called out (hardening checks land before the operator guide that references them), so the post-merge tree is internally consistent.

### Step 6 cross-check — operator guide vs. shipped checks on `origin/main`

Walked every check name referenced in `docs/OPERATOR_GUIDE.md` against `reporium_audit/checks/` on `bfb1366`:

| Reference in guide | Shipped check name | Source |
|---|---|---|
| `reporium-api /health`, `/repos`, `/search` | identical | `checks/api.py:18,32,45` |
| `contract: no private/fork repos exposed` | identical | `checks/contract.py:39` |
| `knowledge graph build freshness` (>25h FAIL) | identical | `checks/knowledge_graph.py:97,107,116` |
| `knowledge graph DEPENDS_ON > 0` | identical | `checks/knowledge_graph.py:126` |
| `knowledge graph edge count regression` (>50% / >20%) | identical | `checks/knowledge_graph.py:134,167,173,182` |
| `cloud run candidate tags` | identical | `checks/cloud_run_tags.py:122,130,143,153,162,204` |
| `reporium-db index.json fresh`, `reporium-db repo count` | identical | `checks/reporium_db.py:28,39,45` |
| `leaks: <repo> README` | identical | `checks/leaks.py:85` |
| `<repo> schedule: <workflow>` | identical | `checks/workflows.py:122` |
| `<repo> CI` | identical | `checks/workflows.py:80` |

No dangling references — the docs PR's pre-merge "strip dangling refs to unshipped checks/reporter" commit did its job. Operator guide is in sync with shipped check vocabulary; no follow-up edit needed from this lane.

### Action taken

- Created this lane log with merge facts and the §6 cross-check.
- Posted a brief post-merge confirmation comment on PRs #11 and #12 naming the merge commit and what was verified.
- No code changes to `reporium_audit/**` or `tests/**` (none warranted).
- Did not push this lane log to remote — it's a local audit-trail artifact for this autonomous run; promoting it to `main` is the operator's call.

### Residual / next checkpoint

The +8h checkpoint (`audit-lane-followup-plus8h-2026-04-26-am`, 01:03 PDT) is still scheduled to run. By that time:
- Tonight's nightly audit (~01:05 PDT cron, 08:05 UTC) should land a `audit: nightly report 2026-04-26` commit on `main`. If it doesn't, that's the §5 signal #6 ("nightly commit missing entirely") and the +8h run should investigate.
- The newly-wired `cloud run candidate tags`, `leaks: …`, `knowledge graph build freshness`, and per-(repo, workflow-name) schedule checks will be exercised for the first time on a real CI run. Expect either new SKIPs (if `GH_TOKEN` / `DATABASE_URL` aren't on the runner) or the first real signal from each.

---

## +8h pre-morning final: 2026-04-26 ~01:03 PDT (08:03 UTC + nightly fired at 08:46 UTC)

**Status changed since +3h: nightly audit FIRED but FAILED.** No `2026-04-26` report was committed to `main`. Root cause is a missing-dep regression in PR #12. Auto-filed alarm landed.

### PR state (post-merge, both unchanged)
| PR | State | Merged at (UTC) | Merge commit |
|---|---|---|---|
| [#11](https://github.com/perditioinc/reporium-audit/pull/11) | MERGED | 2026-04-26 00:29:07 | `bfb1366` |
| [#12](https://github.com/perditioinc/reporium-audit/pull/12) | MERGED | 2026-04-26 00:06:50 | `1002030` |

`origin/main` HEAD = `bfb1366` (no advance since +3h — nightly never reached its commit step).

### Nightly audit run — FIRST RED ON HARDENED CODE
| Field | Value |
|---|---|
| Workflow | Nightly Audit |
| Run | [`24952565529`](https://github.com/perditioinc/reporium-audit/actions/runs/24952565529) |
| Started | 2026-04-26 08:46:21 UTC (~01:46 PDT — ~41 min late vs. `cron: '0 8 * * *'` due to GH scheduler drift, normal) |
| Duration | 12s |
| Conclusion | **failure** |
| Auto-filed issue | [#13 "Audit failure 2026-04-26"](https://github.com/perditioinc/reporium-audit/issues/13), opened 08:46:31 UTC |

### Failure root cause
Step "Run audit" (`python -m reporium_audit run`) crashed at import time:

```
File ".../reporium_audit/__main__.py", line 15, in <module>
    from reporium_audit.checks.knowledge_graph import check_knowledge_graph
File ".../reporium_audit/checks/knowledge_graph.py", line 24, in <module>
    import psycopg2
ModuleNotFoundError: No module named 'psycopg2'
```

This is a **regression from PR #12**. `reporium_audit/checks/knowledge_graph.py:24` introduced a module-top-level `import psycopg2`, but:
- `pyproject.toml` `[project] dependencies` lists only `httpx>=0.27` and `python-dotenv>=1.0`. Neither `psycopg2` nor `psycopg2-binary` is declared (runtime or `dev`).
- `.github/workflows/audit.yml:25` installs with bare `pip install -e .` — pulls only declared deps.
- The check **was designed** to skip cleanly when `DATABASE_URL` is unset (per `checks/knowledge_graph.py:97,107,116,126,134,167,173,182` referenced in §6 cross-check above), but the top-level import means the module never finishes loading on a runner without psycopg2 — skip logic never gets a chance to run.

Local `pytest -q` continued passing on `824cab69` because the developer venv has psycopg2 from another project; CI does not.

### Disposition for the 2026-04-26 morning operator
**Pick one of two fixes (both single-PR, both in scope for `reporium-audit`):**

1. **Add the dep** — append `"psycopg2-binary>=2.9"` to `pyproject.toml` `[project] dependencies`. One line. Pragmatic. Matches the spirit of "the check needs the driver to function." Issue: now every install pulls libpq even when `DATABASE_URL` isn't set.
2. **Move the import inside `check_knowledge_graph()`** (or guard with a `try/except ImportError`). Preserves the skip-when-env-missing contract that other checks already follow. Slightly more code but architecturally consistent.

Recommendation from this lane: **option 2** is the more honest fix because the *contract* the file already implements (skip when no `DATABASE_URL`) is broken by a top-level import that mandates the driver regardless of env. Either is acceptable; option 1 is faster.

After the fix lands, manually re-run via `gh workflow run audit.yml --repo perditioinc/reporium-audit` to seed the missing 2026-04-26 row, OR let the next 08:00 UTC fire (2026-04-27) catch up — the `commit_only_on_diff` step will still create that day's row.

### Residual blind spots from morning note — re-evaluated
- ❌ "Cloud run candidate tags / leaks: … / knowledge graph build freshness / per-(repo, workflow-name) schedule" first-real-run signal — **NOT YET OBSERVED**: the run died at module import, before any of these checks executed. They remain unverified end-to-end on CI. Will be exercised on the first nightly *after* the psycopg2 fix.
- ✅ Operator-guide vs. shipped-checks consistency (§6 cross-check) — still valid; `bfb1366` is unchanged.
- ✅ Auto-failure issue creation pathway — verified working (#13 filed within 10s of failure).

### Cosmetic noise (informational)
Both PRs received an "@-" comment from `perditioinc` at 03:05:43 / 03:05:48 UTC. Body is literally `@-`. Looks like a malformed automated post from a different lane. Not blocking, not from this lane. Worth a quick eyeball during the morning sweep.

### Action taken by this lane
- Appended this +8h block to the lane log.
- Posted a brief comment on PR #12 referencing run `24952565529`, issue #13, and the root cause.
- **Did not** edit code, push to `main`, or open a fix PR — that's the morning operator's call (a fix touches `pyproject.toml` or `checks/knowledge_graph.py` and the +8h scope says "do not merge or deploy"; cutting a fresh PR for a 1-line change in the middle of the night without operator awareness is the wrong default).
- **Did not** push this lane log to remote — same reasoning as the +3h pass; it's a local audit-trail artifact for the operator.

### Final disposition
**Morning queue, in order of priority:**
1. Resolve [#13](https://github.com/perditioinc/reporium-audit/issues/13) by adding `psycopg2-binary` dep or moving the import inside the function (recommend the latter).
2. Manually trigger nightly to seed the 2026-04-26 report row, OR accept the gap.
3. Re-evaluate the four "first-real-run" checks once a clean nightly succeeds — that's where the *actual* hardening signal will surface.
4. (Optional cosmetic) Delete the two stray `@-` comments on PRs #11 / #12.
