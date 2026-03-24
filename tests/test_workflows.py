"""Tests for workflow audit coverage."""

from __future__ import annotations

import httpx
import pytest
import respx

from reporium_audit.checks.workflows import ACTIVE_SUITE_REPOS, check_workflows


def test_active_suite_repos_cover_current_names():
    assert "perditioinc/reporium-scoring" in ACTIVE_SUITE_REPOS
    assert "perditioinc/repo-intelligence" not in ACTIVE_SUITE_REPOS
    assert len(ACTIVE_SUITE_REPOS) == len(set(ACTIVE_SUITE_REPOS))


@pytest.mark.asyncio
@respx.mock
async def test_check_workflows_reports_success_for_latest_run():
    repo = "perditioinc/reporium-scoring"
    respx.get(f"https://api.github.com/repos/{repo}/actions/runs?per_page=1").mock(
        return_value=httpx.Response(
            200,
            json={"workflow_runs": [{"name": "Tests", "conclusion": "success"}]},
        )
    )

    for other_repo in ACTIVE_SUITE_REPOS:
        if other_repo == repo:
            continue
        respx.get(f"https://api.github.com/repos/{other_repo}/actions/runs?per_page=1").mock(
            return_value=httpx.Response(200, json={"workflow_runs": []})
        )

    results = await check_workflows("token")
    scoring = next(result for result in results if result["check"] == "reporium-scoring CI")
    assert scoring["status"] == "PASS"
    assert scoring["detail"] == "Tests: success"


@pytest.mark.asyncio
@respx.mock
async def test_check_workflows_warns_when_repo_has_no_runs():
    repo = "perditioinc/reporium-audit"
    respx.get(f"https://api.github.com/repos/{repo}/actions/runs?per_page=1").mock(
        return_value=httpx.Response(200, json={"workflow_runs": []})
    )

    for other_repo in ACTIVE_SUITE_REPOS:
        if other_repo == repo:
            continue
        respx.get(f"https://api.github.com/repos/{other_repo}/actions/runs?per_page=1").mock(
            return_value=httpx.Response(
                200,
                json={"workflow_runs": [{"name": "Tests", "conclusion": "success"}]},
            )
        )

    results = await check_workflows("token")
    audit = next(result for result in results if result["check"] == "perditioinc/reporium-audit workflows")
    assert audit["status"] == "WARN"
    assert audit["detail"] == "No runs"
