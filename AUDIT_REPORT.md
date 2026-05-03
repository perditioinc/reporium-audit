# Reporium Audit Report — 2026-05-03

## Summary

✓ 32/37 checks passed | ✗ 2 failures | ⚠ 2 warnings

## Failures

- **reporium-api CI**: Tests: None
- **reporium-audit CI**: Nightly Audit: None

## Warnings

- **perditioinc/repo-intelligence workflows**: No runs
- **reporium-api schedule: Data Quality Check**: no recent run with matching workflow name

## Full Results

| Check | Status | Detail |
|-------|--------|--------|
| reporium-api /health | ✓ PASS | {'status': 'ok', 'db': 'ok', 'pool': {'size': 5, 'checked_out': 1, 'overflow': -3}} |
| reporium-api /repos | ✓ PASS | 1867 repos |
| reporium-api /search | ✓ PASS | 20 results |
| contract: privacy field present on every repo | ✓ PASS | all 200 repos carry isPrivate / is_private |
| contract: no private repos exposed | ✓ PASS | 200 repos checked, none private |
| contract: no null required fields | ✓ PASS | 0 nulls |
| contract: no null enriched fields | ✓ PASS | 0 nulls |
| static artifact: reachable | ✓ PASS | 1867 repos at https://reporium.com/data/library.json |
| static artifact: privacy field present on every repo | ✓ PASS | all 1867 repos carry isPrivate / is_private |
| static artifact: no private repos exposed | ✓ PASS | 1867 repos checked, none private |
| cache vs db: repo detail consistency | ✓ PASS | 15/15 sampled repos have /repos/<slug> categories that include the /library/full dbCategory column value |
| reporium-db repo count | ✓ PASS | 1863 repos |
| reporium-db index.json fresh | ✓ PASS | Updated 18.6h ago |
| forksync CI | ✓ PASS | Security Scan: success |
| reporium-db CI | ✓ PASS | Security Scan: success |
| reporium-dataset CI | ✓ PASS | Security Scan: success |
| portfolio CI | ✓ PASS | Security Scan: success |
| reporium-roadmap CI | ✓ PASS | Security Scan: success |
| reporium-metrics CI | ✓ PASS | Security Scan: success |
| perditioinc/repo-intelligence workflows | ⚠ WARN | No runs |
| reporium-api CI | ✗ FAIL | Tests: None |
| reporium-ingestion CI | ✓ PASS | Tests: success |
| reporium-events CI | ✓ PASS | Security Scan: success |
| reporium-audit CI | ✗ FAIL | Nightly Audit: None |
| forksync schedule: Nightly Fork Sync | ✓ PASS | success (started 2026-05-02T07:50:37Z) |
| reporium-db schedule: Nightly Sync | ✓ PASS | success (started 2026-05-02T07:01:49Z) |
| reporium-ingestion schedule: Nightly Graph Build | ✓ PASS | success (started 2026-05-02T16:15:58Z) |
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

*Generated at 2026-05-03T01:40:09.454250+00:00*