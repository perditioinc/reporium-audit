# Reporium Audit Report — 2026-03-23

## Summary

✓ 13/16 checks passed | ✗ 2 failures | ⚠ 1 warnings

## Failures

- **contract: no private/fork repos exposed**: 1406 repos, 1390 private/fork
- **reporium-api CI**: Deploy to Cloud Run: failure

## Warnings

- **perditioinc/repo-intelligence workflows**: No runs

## Full Results

| Check | Status | Detail |
|-------|--------|--------|
| reporium-api /health | ✓ PASS | {'status': 'ok', 'database': 'ok', 'cache': 'ok', 'last_ingestion': {'started_at': '2026-03-22T20:00 |
| reporium-api /repos | ✓ PASS | 1406 repos |
| reporium-api /search | ✓ PASS | 20 results |
| contract: no private/fork repos exposed | ✗ FAIL | 1406 repos, 1390 private/fork |
| contract: no null required fields | ✓ PASS | 0 nulls |
| contract: no null enriched fields | ✓ PASS | 0 nulls |
| reporium-db repo count | ✓ PASS | 1405 repos |
| reporium-db index.json fresh | ✓ PASS | Updated 2.4h ago |
| forksync CI | ✓ PASS | Nightly Fork Sync: success |
| reporium-db CI | ✓ PASS | Nightly Sync: success |
| reporium-dataset CI | ✓ PASS | Nightly README Update: success |
| portfolio CI | ✓ PASS | Nightly Portfolio Update: success |
| reporium-roadmap CI | ✓ PASS | Nightly Roadmap Update: success |
| reporium-metrics CI | ✓ PASS | Nightly Metrics Collection: success |
| perditioinc/repo-intelligence workflows | ⚠ WARN | No runs |
| reporium-api CI | ✗ FAIL | Deploy to Cloud Run: failure |

*Generated at 2026-03-23T08:39:51.918501+00:00*