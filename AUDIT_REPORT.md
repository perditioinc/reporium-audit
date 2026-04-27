# Reporium Audit Report — 2026-04-27

## Summary

✓ 26/32 checks passed | ✗ 4 failures | ⚠ 1 warnings

## Failures

- **reporium-ingestion CI**: Nightly Graph Build: failure
- **reporium-audit CI**: Nightly Audit: None
- **reporium-ingestion schedule: Nightly Graph Build**: failure (started 2026-04-26T09:27:36Z)
- **reporium-api schedule: Data Quality Check**: failure (started 2026-04-26T09:42:15Z)

## Warnings

- **perditioinc/repo-intelligence workflows**: No runs

## Full Results

| Check | Status | Detail |
|-------|--------|--------|
| reporium-api /health | ✓ PASS | {'status': 'ok', 'db': 'ok', 'pool': {'size': 5, 'checked_out': 1, 'overflow': 0}} |
| reporium-api /repos | ✓ PASS | 1861 repos |
| reporium-api /search | ✓ PASS | 20 results |
| contract: no private repos exposed | ✓ PASS | 200 public repos |
| contract: no null required fields | ✓ PASS | 0 nulls |
| contract: no null enriched fields | ✓ PASS | 0 nulls |
| reporium-db repo count | ✓ PASS | 1858 repos |
| reporium-db index.json fresh | ✓ PASS | Updated 18.3h ago |
| forksync CI | ✓ PASS | Security Scan: success |
| reporium-db CI | ✓ PASS | Security Scan: success |
| reporium-dataset CI | ✓ PASS | Security Scan: success |
| portfolio CI | ✓ PASS | Security Scan: success |
| reporium-roadmap CI | ✓ PASS | Security Scan: success |
| reporium-metrics CI | ✓ PASS | Security Scan: success |
| perditioinc/repo-intelligence workflows | ⚠ WARN | No runs |
| reporium-api CI | ✓ PASS | Keep Cloud Run warm: success |
| reporium-ingestion CI | ✗ FAIL | Nightly Graph Build: failure |
| reporium-events CI | ✓ PASS | Security Scan: success |
| reporium-audit CI | ✗ FAIL | Nightly Audit: None |
| forksync schedule: Nightly Fork Sync | ✓ PASS | success (started 2026-04-26T07:46:00Z) |
| reporium-db schedule: Nightly Sync | ✓ PASS | success (started 2026-04-26T06:59:17Z) |
| reporium-ingestion schedule: Nightly Graph Build | ✗ FAIL | failure (started 2026-04-26T09:27:36Z) |
| reporium-api schedule: Data Quality Check | ✗ FAIL | failure (started 2026-04-26T09:42:15Z) |
| knowledge graph edge counts | ? SKIP | DATABASE_URL not set -- audit runner has no DB credentials |
| cloud run candidate tags | ✓ PASS | No candidate tags harvested from recent deploy runs |
| leaks: perditioinc/reporium-api README | ✓ PASS | No forbidden emails |
| leaks: perditioinc/reporium-audit README | ✓ PASS | No forbidden emails |
| leaks: perditioinc/reporium-db README | ✓ PASS | No forbidden emails |
| leaks: perditioinc/portfolio README | ✓ PASS | No forbidden emails |
| leaks: perditioinc/reporium-ingestion README | ✓ PASS | No forbidden emails |
| leaks: perditioinc/reporium-events README | ✓ PASS | No forbidden emails |
| leaks: perditioinc/reporium-metrics README | ✓ PASS | No forbidden emails |

*Generated at 2026-04-27T01:18:31.079411+00:00*