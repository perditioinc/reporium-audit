# Reporium Audit Report — 2026-06-07

## Summary

✓ 31/37 checks passed | ✗ 4 failures | ⚠ 1 warnings

## Failures

- **reporium-db index.json fresh**: Updated 26.4h ago
- **forksync CI**: Nightly Fork Sync: failure
- **reporium-audit CI**: Nightly Audit: None
- **forksync schedule: Nightly Fork Sync**: failure (started 2026-06-07T09:21:16Z)

## Warnings

- **perditioinc/repo-intelligence workflows**: No runs

## Full Results

| Check | Status | Detail |
|-------|--------|--------|
| reporium-api /health | ✓ PASS | {'status': 'ok', 'db': 'ok', 'pool': {'size': 5, 'checked_out': 2, 'overflow': 0}} |
| reporium-api /repos | ✓ PASS | 1944 repos |
| reporium-api /search | ✓ PASS | 20 results |
| contract: privacy field present on every repo | ✓ PASS | all 200 repos carry isPrivate / is_private |
| contract: no private repos exposed | ✓ PASS | 200 repos checked, none private |
| contract: no null required fields | ✓ PASS | 0 nulls |
| contract: no null enriched fields | ✓ PASS | 0 nulls |
| static artifact: reachable | ✓ PASS | 1944 repos at https://reporium.com/data/library.json |
| static artifact: privacy field present on every repo | ✓ PASS | all 1944 repos carry isPrivate / is_private |
| static artifact: no private repos exposed | ✓ PASS | 1944 repos checked, none private |
| cache vs db: repo detail consistency | ✓ PASS | 15/15 sampled repos have /repos/<slug> categories that include the /library/full dbCategory column value |
| reporium-db repo count | ✓ PASS | 1939 repos |
| reporium-db index.json fresh | ✗ FAIL | Updated 26.4h ago |
| forksync CI | ✗ FAIL | Nightly Fork Sync: failure |
| reporium-db CI | ✓ PASS | Tests: success |
| reporium-dataset CI | ✓ PASS | Tests: success |
| portfolio CI | ✓ PASS | Nightly Portfolio Update: success |
| reporium-roadmap CI | ✓ PASS | Nightly Roadmap Update: success |
| reporium-metrics CI | ✓ PASS | Nightly Metrics Collection: success |
| perditioinc/repo-intelligence workflows | ⚠ WARN | No runs |
| reporium-api CI | ✓ PASS | Nightly Sync from reporium-db: success |
| reporium-ingestion CI | ✓ PASS | Tests: success |
| reporium-events CI | ✓ PASS | Security Scan: success |
| reporium-audit CI | ✗ FAIL | Nightly Audit: None |
| forksync schedule: Nightly Fork Sync | ✗ FAIL | failure (started 2026-06-07T09:21:16Z) |
| reporium-db schedule: Nightly Sync | ✓ PASS | success (started 2026-06-07T08:24:24Z) |
| reporium-ingestion schedule: Nightly Graph Build | ✓ PASS | success (started 2026-06-06T15:50:24Z) |
| reporium-api schedule: Data Quality Check | ✓ PASS | success (started 2026-06-06T10:48:16Z) |
| knowledge graph edge counts | ? SKIP | DATABASE_URL not set -- audit runner has no DB credentials |
| cloud run candidate tags | ✓ PASS | No candidate tags harvested from recent deploy runs |
| leaks: perditioinc/reporium-api README | ✓ PASS | No forbidden emails |
| leaks: perditioinc/reporium-audit README | ✓ PASS | No forbidden emails |
| leaks: perditioinc/reporium-db README | ✓ PASS | No forbidden emails |
| leaks: perditioinc/portfolio README | ✓ PASS | No forbidden emails |
| leaks: perditioinc/reporium-ingestion README | ✓ PASS | No forbidden emails |
| leaks: perditioinc/reporium-events README | ✓ PASS | No forbidden emails |
| leaks: perditioinc/reporium-metrics README | ✓ PASS | No forbidden emails |

*Generated at 2026-06-07T10:18:09.984930+00:00*