# Reporium Audit Report — 2026-05-28

## Summary

✓ 28/37 checks passed | ✗ 7 failures | ⚠ 1 warnings

## Failures

- **reporium-db index.json fresh**: Updated 99.5h ago
- **forksync CI**: Nightly Fork Sync: failure
- **reporium-db CI**: Nightly Sync: failure
- **reporium-ingestion CI**: Nightly Enrichment Quality Probe: failure
- **reporium-audit CI**: Nightly Audit: None
- **forksync schedule: Nightly Fork Sync**: failure (started 2026-05-28T10:12:21Z)
- **reporium-db schedule: Nightly Sync**: failure (started 2026-05-28T08:43:02Z)

## Warnings

- **perditioinc/repo-intelligence workflows**: No runs

## Full Results

| Check | Status | Detail |
|-------|--------|--------|
| reporium-api /health | ✓ PASS | {'status': 'ok', 'db': 'ok', 'pool': {'size': 5, 'checked_out': 1, 'overflow': 0}} |
| reporium-api /repos | ✓ PASS | 1930 repos |
| reporium-api /search | ✓ PASS | 20 results |
| contract: privacy field present on every repo | ✓ PASS | all 200 repos carry isPrivate / is_private |
| contract: no private repos exposed | ✓ PASS | 200 repos checked, none private |
| contract: no null required fields | ✓ PASS | 0 nulls |
| contract: no null enriched fields | ✓ PASS | 0 nulls |
| static artifact: reachable | ✓ PASS | 1930 repos at https://reporium.com/data/library.json |
| static artifact: privacy field present on every repo | ✓ PASS | all 1930 repos carry isPrivate / is_private |
| static artifact: no private repos exposed | ✓ PASS | 1930 repos checked, none private |
| cache vs db: repo detail consistency | ✓ PASS | 15/15 sampled repos have /repos/<slug> categories that include the /library/full dbCategory column value |
| reporium-db repo count | ✓ PASS | 1926 repos |
| reporium-db index.json fresh | ✗ FAIL | Updated 99.5h ago |
| forksync CI | ✗ FAIL | Nightly Fork Sync: failure |
| reporium-db CI | ✗ FAIL | Nightly Sync: failure |
| reporium-dataset CI | ✓ PASS | Nightly README Update: success |
| portfolio CI | ✓ PASS | Nightly Portfolio Update: success |
| reporium-roadmap CI | ✓ PASS | Nightly Roadmap Update: success |
| reporium-metrics CI | ✓ PASS | Nightly Metrics Collection: success |
| perditioinc/repo-intelligence workflows | ⚠ WARN | No runs |
| reporium-api CI | ✓ PASS | Nightly Sync from reporium-db: success |
| reporium-ingestion CI | ✗ FAIL | Nightly Enrichment Quality Probe: failure |
| reporium-events CI | ✓ PASS | Security Scan: success |
| reporium-audit CI | ✗ FAIL | Nightly Audit: None |
| forksync schedule: Nightly Fork Sync | ✗ FAIL | failure (started 2026-05-28T10:12:21Z) |
| reporium-db schedule: Nightly Sync | ✗ FAIL | failure (started 2026-05-28T08:43:02Z) |
| reporium-ingestion schedule: Nightly Graph Build | ✓ PASS | success (started 2026-05-27T17:41:07Z) |
| reporium-api schedule: Data Quality Check | ✓ PASS | success (started 2026-05-27T12:09:25Z) |
| knowledge graph edge counts | ? SKIP | DATABASE_URL not set -- audit runner has no DB credentials |
| cloud run candidate tags | ✓ PASS | No candidate tags harvested from recent deploy runs |
| leaks: perditioinc/reporium-api README | ✓ PASS | No forbidden emails |
| leaks: perditioinc/reporium-audit README | ✓ PASS | No forbidden emails |
| leaks: perditioinc/reporium-db README | ✓ PASS | No forbidden emails |
| leaks: perditioinc/portfolio README | ✓ PASS | No forbidden emails |
| leaks: perditioinc/reporium-ingestion README | ✓ PASS | No forbidden emails |
| leaks: perditioinc/reporium-events README | ✓ PASS | No forbidden emails |
| leaks: perditioinc/reporium-metrics README | ✓ PASS | No forbidden emails |

*Generated at 2026-05-28T11:25:42.872232+00:00*