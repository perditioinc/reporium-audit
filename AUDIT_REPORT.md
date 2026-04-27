# Reporium Audit Report — 2026-04-27

## Summary

✓ 28/32 checks passed | ✗ 2 failures | ⚠ 1 warnings

## Failures

- **reporium-audit CI**: Nightly Audit: None
- **reporium-api schedule: Data Quality Check**: failure (started 2026-04-27T01:56:44Z)

## Warnings

- **perditioinc/repo-intelligence workflows**: No runs

## Full Results

| Check | Status | Detail |
|-------|--------|--------|
| reporium-api /health | ✓ PASS | {'status': 'ok', 'db': 'ok', 'pool': {'size': 5, 'checked_out': 2, 'overflow': 0}} |
| reporium-api /repos | ✓ PASS | 1862 repos |
| reporium-api /search | ✓ PASS | 20 results |
| contract: no private repos exposed | ✓ PASS | 200 public repos |
| contract: no null required fields | ✓ PASS | 0 nulls |
| contract: no null enriched fields | ✓ PASS | 0 nulls |
| reporium-db repo count | ✓ PASS | 1858 repos |
| reporium-db index.json fresh | ✓ PASS | Updated 2.3h ago |
| forksync CI | ✓ PASS | Nightly Fork Sync: success |
| reporium-db CI | ✓ PASS | Nightly Sync: success |
| reporium-dataset CI | ✓ PASS | Nightly README Update: success |
| portfolio CI | ✓ PASS | Nightly Portfolio Update: success |
| reporium-roadmap CI | ✓ PASS | Nightly Roadmap Update: success |
| reporium-metrics CI | ✓ PASS | Nightly Metrics Collection: success |
| perditioinc/repo-intelligence workflows | ⚠ WARN | No runs |
| reporium-api CI | ✓ PASS | Tests: success |
| reporium-ingestion CI | ✓ PASS | Tests: success |
| reporium-events CI | ✓ PASS | Security Scan: success |
| reporium-audit CI | ✗ FAIL | Nightly Audit: None |
| forksync schedule: Nightly Fork Sync | ✓ PASS | success (started 2026-04-27T08:33:18Z) |
| reporium-db schedule: Nightly Sync | ✓ PASS | success (started 2026-04-27T07:35:07Z) |
| reporium-ingestion schedule: Nightly Graph Build | ✓ PASS | success (started 2026-04-27T07:53:46Z) |
| reporium-api schedule: Data Quality Check | ✗ FAIL | failure (started 2026-04-27T01:56:44Z) |
| knowledge graph edge counts | ? SKIP | DATABASE_URL not set -- audit runner has no DB credentials |
| cloud run candidate tags | ✓ PASS | No candidate tags harvested from recent deploy runs |
| leaks: perditioinc/reporium-api README | ✓ PASS | No forbidden emails |
| leaks: perditioinc/reporium-audit README | ✓ PASS | No forbidden emails |
| leaks: perditioinc/reporium-db README | ✓ PASS | No forbidden emails |
| leaks: perditioinc/portfolio README | ✓ PASS | No forbidden emails |
| leaks: perditioinc/reporium-ingestion README | ✓ PASS | No forbidden emails |
| leaks: perditioinc/reporium-events README | ✓ PASS | No forbidden emails |
| leaks: perditioinc/reporium-metrics README | ✓ PASS | No forbidden emails |

*Generated at 2026-04-27T10:01:43.595018+00:00*