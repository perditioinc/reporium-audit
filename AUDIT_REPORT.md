# Reporium Audit Report — 2026-04-28

## Summary

✓ 25/32 checks passed | ✗ 4 failures | ⚠ 2 warnings

## Failures

- **reporium-db index.json fresh**: Updated 26.3h ago
- **reporium-db CI**: Nightly Sync: failure
- **reporium-audit CI**: Nightly Audit: None
- **reporium-db schedule: Nightly Sync**: failure (started 2026-04-28T07:31:45Z)

## Warnings

- **perditioinc/repo-intelligence workflows**: No runs
- **reporium-api schedule: Data Quality Check**: no recent run with matching workflow name

## Full Results

| Check | Status | Detail |
|-------|--------|--------|
| reporium-api /health | ✓ PASS | {'status': 'ok', 'db': 'ok', 'pool': {'size': 5, 'checked_out': 2, 'overflow': 0}} |
| reporium-api /repos | ✓ PASS | 1861 repos |
| reporium-api /search | ✓ PASS | 20 results |
| contract: no private repos exposed | ✓ PASS | 200 public repos |
| contract: no null required fields | ✓ PASS | 0 nulls |
| contract: no null enriched fields | ✓ PASS | 0 nulls |
| reporium-db repo count | ✓ PASS | 1858 repos |
| reporium-db index.json fresh | ✗ FAIL | Updated 26.3h ago |
| forksync CI | ✓ PASS | Nightly Fork Sync: success |
| reporium-db CI | ✗ FAIL | Nightly Sync: failure |
| reporium-dataset CI | ✓ PASS | Nightly README Update: success |
| portfolio CI | ✓ PASS | Nightly Portfolio Update: success |
| reporium-roadmap CI | ✓ PASS | Nightly Roadmap Update: success |
| reporium-metrics CI | ✓ PASS | Nightly Metrics Collection: success |
| perditioinc/repo-intelligence workflows | ⚠ WARN | No runs |
| reporium-api CI | ✓ PASS | Nightly Sync from reporium-db: success |
| reporium-ingestion CI | ✓ PASS | Manual Ingestion Run: success |
| reporium-events CI | ✓ PASS | Security Scan: success |
| reporium-audit CI | ✗ FAIL | Nightly Audit: None |
| forksync schedule: Nightly Fork Sync | ✓ PASS | success (started 2026-04-28T08:31:42Z) |
| reporium-db schedule: Nightly Sync | ✗ FAIL | failure (started 2026-04-28T07:31:45Z) |
| reporium-ingestion schedule: Nightly Graph Build | ✓ PASS | success (started 2026-04-27T10:28:51Z) |
| reporium-api schedule: Data Quality Check | ⚠ WARN | no recent run with matching workflow name |
| knowledge graph edge counts | ? SKIP | DATABASE_URL not set -- audit runner has no DB credentials |
| cloud run candidate tags | ✓ PASS | No candidate tags harvested from recent deploy runs |
| leaks: perditioinc/reporium-api README | ✓ PASS | No forbidden emails |
| leaks: perditioinc/reporium-audit README | ✓ PASS | No forbidden emails |
| leaks: perditioinc/reporium-db README | ✓ PASS | No forbidden emails |
| leaks: perditioinc/portfolio README | ✓ PASS | No forbidden emails |
| leaks: perditioinc/reporium-ingestion README | ✓ PASS | No forbidden emails |
| leaks: perditioinc/reporium-events README | ✓ PASS | No forbidden emails |
| leaks: perditioinc/reporium-metrics README | ✓ PASS | No forbidden emails |

*Generated at 2026-04-28T10:03:15.134708+00:00*