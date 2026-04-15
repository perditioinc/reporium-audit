# Reporium Audit Report — 2026-04-15

## Summary

✓ 8/14 checks passed | ✗ 5 failures | ⚠ 1 warnings

## Failures

- **contract: /library/full reachable**: HTTP 500
- **reporium-db index.json fresh**: Updated 122.1h ago
- **reporium-db CI**: Nightly Sync: failure
- **portfolio CI**: Nightly Portfolio Update: failure
- **reporium-api CI**: Tests: failure

## Warnings

- **perditioinc/repo-intelligence workflows**: No runs

## Full Results

| Check | Status | Detail |
|-------|--------|--------|
| reporium-api /health | ✓ PASS | {'status': 'ok', 'db': 'ok'} |
| reporium-api /repos | ✓ PASS | 1641 repos |
| reporium-api /search | ✓ PASS | 20 results |
| contract: /library/full reachable | ✗ FAIL | HTTP 500 |
| reporium-db repo count | ✓ PASS | 1822 repos |
| reporium-db index.json fresh | ✗ FAIL | Updated 122.1h ago |
| forksync CI | ✓ PASS | Nightly Fork Sync: success |
| reporium-db CI | ✗ FAIL | Nightly Sync: failure |
| reporium-dataset CI | ✓ PASS | Nightly README Update: success |
| portfolio CI | ✗ FAIL | Nightly Portfolio Update: failure |
| reporium-roadmap CI | ✓ PASS | Nightly Roadmap Update: success |
| reporium-metrics CI | ✓ PASS | Nightly Metrics Collection: success |
| perditioinc/repo-intelligence workflows | ⚠ WARN | No runs |
| reporium-api CI | ✗ FAIL | Tests: failure |

*Generated at 2026-04-15T09:08:01.380783+00:00*