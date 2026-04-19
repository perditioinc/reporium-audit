# Reporium Audit Report — 2026-04-19

## Summary

✓ 11/16 checks passed | ✗ 4 failures | ⚠ 1 warnings

## Failures

- **contract: no private/fork repos exposed**: 200 repos, 200 private/fork
- **reporium-db index.json fresh**: Updated 217.7h ago
- **reporium-db CI**: Nightly Sync: failure
- **portfolio CI**: Nightly Portfolio Update: failure

## Warnings

- **perditioinc/repo-intelligence workflows**: No runs

## Full Results

| Check | Status | Detail |
|-------|--------|--------|
| reporium-api /health | ✓ PASS | {'status': 'ok', 'db': 'ok'} |
| reporium-api /repos | ✓ PASS | 1825 repos |
| reporium-api /search | ✓ PASS | 20 results |
| contract: no private/fork repos exposed | ✗ FAIL | 200 repos, 200 private/fork |
| contract: no null required fields | ✓ PASS | 0 nulls |
| contract: no null enriched fields | ✓ PASS | 0 nulls |
| reporium-db repo count | ✓ PASS | 1822 repos |
| reporium-db index.json fresh | ✗ FAIL | Updated 217.7h ago |
| forksync CI | ✓ PASS | Nightly Fork Sync: success |
| reporium-db CI | ✗ FAIL | Nightly Sync: failure |
| reporium-dataset CI | ✓ PASS | Nightly README Update: success |
| portfolio CI | ✗ FAIL | Nightly Portfolio Update: failure |
| reporium-roadmap CI | ✓ PASS | Nightly Roadmap Update: success |
| reporium-metrics CI | ✓ PASS | Nightly Metrics Collection: success |
| perditioinc/repo-intelligence workflows | ⚠ WARN | No runs |
| reporium-api CI | ✓ PASS | Keep Cloud Run warm: success |

*Generated at 2026-04-19T08:40:04.753168+00:00*