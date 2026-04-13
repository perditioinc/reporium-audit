# Reporium Audit Report — 2026-04-13

## Summary

✓ 5/14 checks passed | ✗ 8 failures | ⚠ 1 warnings

## Failures

- **reporium-api /health**: {'status': 'degraded', 'db': 'error', 'detail': 'database check failed'}
- **reporium-api /repos**: Expecting value: line 1 column 1 (char 0)
- **reporium-api /search**: Expecting value: line 1 column 1 (char 0)
- **contract: /library/full reachable**: HTTP 500
- **reporium-db index.json fresh**: Updated 74.4h ago
- **reporium-db CI**: Nightly Sync: failure
- **portfolio CI**: Nightly Portfolio Update: failure
- **reporium-api CI**: Nightly Sync from reporium-db: failure

## Warnings

- **perditioinc/repo-intelligence workflows**: No runs

## Full Results

| Check | Status | Detail |
|-------|--------|--------|
| reporium-api /health | ✗ FAIL | {'status': 'degraded', 'db': 'error', 'detail': 'database check failed'} |
| reporium-api /repos | ✗ FAIL | Expecting value: line 1 column 1 (char 0) |
| reporium-api /search | ✗ FAIL | Expecting value: line 1 column 1 (char 0) |
| contract: /library/full reachable | ✗ FAIL | HTTP 500 |
| reporium-db repo count | ✓ PASS | 1822 repos |
| reporium-db index.json fresh | ✗ FAIL | Updated 74.4h ago |
| forksync CI | ✓ PASS | Nightly Fork Sync: success |
| reporium-db CI | ✗ FAIL | Nightly Sync: failure |
| reporium-dataset CI | ✓ PASS | Nightly README Update: success |
| portfolio CI | ✗ FAIL | Nightly Portfolio Update: failure |
| reporium-roadmap CI | ✓ PASS | Nightly Roadmap Update: success |
| reporium-metrics CI | ✓ PASS | Nightly Metrics Collection: success |
| perditioinc/repo-intelligence workflows | ⚠ WARN | No runs |
| reporium-api CI | ✗ FAIL | Nightly Sync from reporium-db: failure |

*Generated at 2026-04-13T09:23:09.737659+00:00*