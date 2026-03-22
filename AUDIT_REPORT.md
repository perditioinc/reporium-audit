# Reporium Audit Report — 2026-03-22

## Summary

✓ 9/13 checks passed | ✗ 3 failures | ⚠ 1 warnings

## Failures

- **reporium-db index.json fresh**: Updated 26.6h ago
- **reporium-db CI**: Nightly Sync: failure
- **reporium-api CI**: Nightly Sync from reporium-db: failure

## Warnings

- **perditioinc/repo-intelligence workflows**: No runs

## Full Results

| Check | Status | Detail |
|-------|--------|--------|
| reporium-api /health | ✓ PASS | {'status': 'ok', 'database': 'ok', 'cache': 'ok', 'last_ingestion': {'started_at': '2026-03-21T09:00 |
| reporium-api /repos | ✓ PASS | 858 repos |
| reporium-api /search | ✓ PASS | 20 results |
| reporium-db repo count | ✓ PASS | 831 repos |
| reporium-db index.json fresh | ✗ FAIL | Updated 26.6h ago |
| forksync CI | ✓ PASS | Nightly Fork Sync: success |
| reporium-db CI | ✗ FAIL | Nightly Sync: failure |
| reporium-dataset CI | ✓ PASS | Nightly README Update: success |
| portfolio CI | ✓ PASS | Nightly Portfolio Update: success |
| reporium-roadmap CI | ✓ PASS | Nightly Roadmap Update: success |
| reporium-metrics CI | ✓ PASS | Nightly Metrics Collection: success |
| perditioinc/repo-intelligence workflows | ⚠ WARN | No runs |
| reporium-api CI | ✗ FAIL | Nightly Sync from reporium-db: failure |

*Generated at 2026-03-22T08:19:09.067601+00:00*