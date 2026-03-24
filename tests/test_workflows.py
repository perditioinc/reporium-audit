from reporium_audit.checks.workflows import ACTIVE_SUITE_REPOS


def test_active_suite_repos_match_current_suite() -> None:
    assert ACTIVE_SUITE_REPOS == [
        "perditioinc/reporium",
        "perditioinc/reporium-api",
        "perditioinc/reporium-audit",
        "perditioinc/reporium-db",
        "perditioinc/reporium-dataset",
        "perditioinc/reporium-events",
        "perditioinc/reporium-ingestion",
        "perditioinc/reporium-metrics",
        "perditioinc/reporium-roadmap",
        "perditioinc/reporium-scoring",
        "perditioinc/reporium-security",
        "perditioinc/reporium-system-design",
    ]


def test_legacy_repo_intelligence_alias_is_removed() -> None:
    assert "perditioinc/repo-intelligence" not in ACTIVE_SUITE_REPOS
