# Reporium Audit Report — 2026-03-21

## Summary

✓ 11/13 checks passed | ✗ 1 failures | ⚠ 1 warnings

## Failures

- **reporium-api CI**: Nightly Sync from reporium-db: failure

## Warnings

- **perditioinc/repo-intelligence workflows**: No runs

## Full Results

| Check | Status | Detail |
|-------|--------|--------|
| reporium-api /health | ✓ PASS | {'status': 'ok', 'database': 'ok', 'cache': 'disabled', 'last_ingestion': None} |
| reporium-api /repos | ✓ PASS | 826 repos |
| reporium-api /search | ✓ PASS | 20 results |
| reporium-db repo count | ✓ PASS | 831 repos |
| reporium-db index.json fresh | ✓ PASS | Updated 2.5h ago |
| forksync CI | ✓ PASS | Nightly Fork Sync: success |
| reporium-db CI | ✓ PASS | Nightly Sync: success |
| reporium-dataset CI | ✓ PASS | Nightly README Update: success |
| portfolio CI | ✓ PASS | Nightly Portfolio Update: success |
| reporium-roadmap CI | ✓ PASS | Nightly Roadmap Update: success |
| reporium-metrics CI | ✓ PASS | Nightly Metrics Collection: success |
| perditioinc/repo-intelligence workflows | ⚠ WARN | No runs |
| reporium-api CI | ✗ FAIL | Nightly Sync from reporium-db: failure |

*Generated at 2026-03-21T08:17:28.474595+00:00*