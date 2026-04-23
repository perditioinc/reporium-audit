# Reporium Audit Report — 2026-04-23

## Summary

✓ 13/16 checks passed | ✗ 2 failures | ⚠ 1 warnings

## Failures

- **contract: no private/fork repos exposed**: 200 repos, 200 private/fork
- **reporium-api CI**: Nightly Sync from reporium-db: failure

## Warnings

- **perditioinc/repo-intelligence workflows**: No runs

## Full Results

| Check | Status | Detail |
|-------|--------|--------|
| reporium-api /health | ✓ PASS | {'status': 'ok', 'db': 'ok'} |
| reporium-api /repos | ✓ PASS | 1855 repos |
| reporium-api /search | ✓ PASS | 20 results |
| contract: no private/fork repos exposed | ✗ FAIL | 200 repos, 200 private/fork |
| contract: no null required fields | ✓ PASS | 0 nulls |
| contract: no null enriched fields | ✓ PASS | 0 nulls |
| reporium-db repo count | ✓ PASS | 1852 repos |
| reporium-db index.json fresh | ✓ PASS | Updated 2.1h ago |
| forksync CI | ✓ PASS | Nightly Fork Sync: success |
| reporium-db CI | ✓ PASS | Nightly Sync: success |
| reporium-dataset CI | ✓ PASS | Nightly README Update: success |
| portfolio CI | ✓ PASS | Nightly Portfolio Update: success |
| reporium-roadmap CI | ✓ PASS | Nightly Roadmap Update: success |
| reporium-metrics CI | ✓ PASS | Nightly Metrics Collection: success |
| perditioinc/repo-intelligence workflows | ⚠ WARN | No runs |
| reporium-api CI | ✗ FAIL | Nightly Sync from reporium-db: failure |

*Generated at 2026-04-23T09:15:58.105475+00:00*