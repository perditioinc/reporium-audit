# Reporium Audit Report — 2026-04-01

## Summary

✓ 9/14 checks passed | ✗ 4 failures | ⚠ 1 warnings

## Failures

- **reporium-api /repos**: 
- **contract: /library/full validation**: 
- **reporium-db index.json fresh**: Updated 49.9h ago
- **reporium-db CI**: Nightly Sync: failure

## Warnings

- **perditioinc/repo-intelligence workflows**: No runs

## Full Results

| Check | Status | Detail |
|-------|--------|--------|
| reporium-api /health | ✓ PASS | {'status': 'ok', 'db': 'ok'} |
| reporium-api /repos | ✗ FAIL |  |
| reporium-api /search | ✓ PASS | 20 results |
| contract: /library/full validation | ✗ FAIL |  |
| reporium-db repo count | ✓ PASS | 1573 repos |
| reporium-db index.json fresh | ✗ FAIL | Updated 49.9h ago |
| forksync CI | ✓ PASS | Nightly Fork Sync: success |
| reporium-db CI | ✗ FAIL | Nightly Sync: failure |
| reporium-dataset CI | ✓ PASS | Nightly README Update: success |
| portfolio CI | ✓ PASS | Nightly Portfolio Update: success |
| reporium-roadmap CI | ✓ PASS | Nightly Roadmap Update: success |
| reporium-metrics CI | ✓ PASS | Nightly Metrics Collection: success |
| perditioinc/repo-intelligence workflows | ⚠ WARN | No runs |
| reporium-api CI | ✓ PASS | Keep Cloud Run warm: success |

*Generated at 2026-04-01T08:51:44.178720+00:00*