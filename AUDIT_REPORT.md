# Reporium Audit Report — 2026-04-07

## Summary

✓ 6/16 checks passed | ✗ 2 failures | ⚠ 8 warnings

## Failures

- **contract: no private/fork repos exposed**: 200 repos, 200 private/fork
- **reporium-db index.json fresh**: Updated 25.8h ago

## Warnings

- **perditioinc/forksync workflows**: No runs
- **perditioinc/reporium-db workflows**: No runs
- **perditioinc/reporium-dataset workflows**: No runs
- **perditioinc/portfolio workflows**: No runs
- **perditioinc/reporium-roadmap workflows**: No runs
- **perditioinc/reporium-metrics workflows**: No runs
- **perditioinc/repo-intelligence workflows**: No runs
- **perditioinc/reporium-api workflows**: No runs

## Full Results

| Check | Status | Detail |
|-------|--------|--------|
| reporium-api /health | ✓ PASS | {'status': 'ok', 'db': 'ok'} |
| reporium-api /repos | ✓ PASS | 1641 repos |
| reporium-api /search | ✓ PASS | 20 results |
| contract: no private/fork repos exposed | ✗ FAIL | 200 repos, 200 private/fork |
| contract: no null required fields | ✓ PASS | 0 nulls |
| contract: no null enriched fields | ✓ PASS | 0 nulls |
| reporium-db repo count | ✓ PASS | 1732 repos |
| reporium-db index.json fresh | ✗ FAIL | Updated 25.8h ago |
| perditioinc/forksync workflows | ⚠ WARN | No runs |
| perditioinc/reporium-db workflows | ⚠ WARN | No runs |
| perditioinc/reporium-dataset workflows | ⚠ WARN | No runs |
| perditioinc/portfolio workflows | ⚠ WARN | No runs |
| perditioinc/reporium-roadmap workflows | ⚠ WARN | No runs |
| perditioinc/reporium-metrics workflows | ⚠ WARN | No runs |
| perditioinc/repo-intelligence workflows | ⚠ WARN | No runs |
| perditioinc/reporium-api workflows | ⚠ WARN | No runs |

*Generated at 2026-04-07T08:49:25.684453+00:00*