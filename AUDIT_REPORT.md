# Reporium Audit Report — 2026-04-29

## Summary

✓ 29/32 checks passed | ✗ 1 failures | ⚠ 1 warnings

## Failures

- **reporium-audit CI**: Nightly Audit: None

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
| reporium-db index.json fresh | ✓ PASS | Updated 2.3h ago |
| forksync CI | ✓ PASS | Nightly Fork Sync: success |
| reporium-db CI | ✓ PASS | Nightly Sync: success |
| reporium-dataset CI | ✓ PASS | Nightly README Update: success |
| portfolio CI | ✓ PASS | Nightly Portfolio Update: success |
| reporium-roadmap CI | ✓ PASS | Nightly Roadmap Update: success |
| reporium-metrics CI | ✓ PASS | Nightly Metrics Collection: success |
| perditioinc/repo-intelligence workflows | ⚠ WARN | No runs |
| reporium-api CI | ✓ PASS | Nightly Sync from reporium-db: success |
| reporium-ingestion CI | ✓ PASS | Nightly Graph Build: success |
| reporium-events CI | ✓ PASS | Security Scan: success |
| reporium-audit CI | ✗ FAIL | Nightly Audit: None |
| forksync schedule: Nightly Fork Sync | ✓ PASS | success (started 2026-04-29T08:25:35Z) |
| reporium-db schedule: Nightly Sync | ✓ PASS | success (started 2026-04-29T07:25:05Z) |
| reporium-ingestion schedule: Nightly Graph Build | ✓ PASS | success (started 2026-04-28T10:27:44Z) |
| reporium-api schedule: Data Quality Check | ✓ PASS | success (started 2026-04-28T10:52:42Z) |
| knowledge graph edge counts | ? SKIP | DATABASE_URL not set -- audit runner has no DB credentials |
| cloud run candidate tags | ✓ PASS | No candidate tags harvested from recent deploy runs |
| leaks: perditioinc/reporium-api README | ✓ PASS | No forbidden emails |
| leaks: perditioinc/reporium-audit README | ✓ PASS | No forbidden emails |
| leaks: perditioinc/reporium-db README | ✓ PASS | No forbidden emails |
| leaks: perditioinc/portfolio README | ✓ PASS | No forbidden emails |
| leaks: perditioinc/reporium-ingestion README | ✓ PASS | No forbidden emails |
| leaks: perditioinc/reporium-events README | ✓ PASS | No forbidden emails |
| leaks: perditioinc/reporium-metrics README | ✓ PASS | No forbidden emails |

*Generated at 2026-04-29T09:53:44.192598+00:00*