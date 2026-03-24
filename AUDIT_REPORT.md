# Reporium Audit Report — 2026-03-24

## Summary

✓ 14/16 checks passed | ✗ 1 failures | ⚠ 1 warnings

## Failures

- **contract: no private/fork repos exposed**: 200 repos, 200 private/fork

## Warnings

- **perditioinc/repo-intelligence workflows**: No runs

## Full Results

| Check | Status | Detail |
|-------|--------|--------|
| reporium-api /health | ✓ PASS | {'status': 'ok', 'database': 'ok', 'cache': 'ok', 'last_ingestion': {'started_at': '2026-03-22T20:00 |
| reporium-api /repos | ✓ PASS | 1460 repos |
| reporium-api /search | ✓ PASS | 20 results |
| contract: no private/fork repos exposed | ✗ FAIL | 200 repos, 200 private/fork |
| contract: no null required fields | ✓ PASS | 0 nulls |
| contract: no null enriched fields | ✓ PASS | 0 nulls |
| reporium-db repo count | ✓ PASS | 1459 repos |
| reporium-db index.json fresh | ✓ PASS | Updated 2.5h ago |
| forksync CI | ✓ PASS | Nightly Fork Sync: success |
| reporium-db CI | ✓ PASS | Tests: success |
| reporium-dataset CI | ✓ PASS | Nightly README Update: success |
| portfolio CI | ✓ PASS | Nightly Portfolio Update: success |
| reporium-roadmap CI | ✓ PASS | Tests: success |
| reporium-metrics CI | ✓ PASS | Tests: success |
| perditioinc/repo-intelligence workflows | ⚠ WARN | No runs |
| reporium-api CI | ✓ PASS | Dev Tests: success |

*Generated at 2026-03-24T08:36:18.466114+00:00*