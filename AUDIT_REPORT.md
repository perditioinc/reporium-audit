# Reporium Audit Report — 2026-04-02

## Summary

✓ 10/14 checks passed | ✗ 3 failures | ⚠ 1 warnings

## Failures

- **contract: /library/full validation**: 
- **reporium-db index.json fresh**: Updated 73.7h ago
- **reporium-db CI**: Nightly Sync: failure

## Warnings

- **perditioinc/repo-intelligence workflows**: No runs

## Full Results

| Check | Status | Detail |
|-------|--------|--------|
| reporium-api /health | ✓ PASS | {'status': 'ok', 'db': 'ok'} |
| reporium-api /repos | ✓ PASS | 1576 repos |
| reporium-api /search | ✓ PASS | 20 results |
| contract: /library/full validation | ✗ FAIL |  |
| reporium-db repo count | ✓ PASS | 1573 repos |
| reporium-db index.json fresh | ✗ FAIL | Updated 73.7h ago |
| forksync CI | ✓ PASS | Nightly Fork Sync: success |
| reporium-db CI | ✗ FAIL | Nightly Sync: failure |
| reporium-dataset CI | ✓ PASS | Nightly README Update: success |
| portfolio CI | ✓ PASS | Nightly Portfolio Update: success |
| reporium-roadmap CI | ✓ PASS | Nightly Roadmap Update: success |
| reporium-metrics CI | ✓ PASS | Nightly Metrics Collection: success |
| perditioinc/repo-intelligence workflows | ⚠ WARN | No runs |
| reporium-api CI | ✓ PASS | Keep Cloud Run warm: success |

*Generated at 2026-04-02T08:42:47.088673+00:00*