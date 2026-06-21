"""Tests for workflow + scheduled-workflow checks.

Uses respx to mock GitHub Actions API responses and verifies that the
scheduled check correctly distinguishes a green ``workflow_dispatch`` run
from a red scheduled run — the pattern behind the 2026-04-23 Data Quality
Check misses. Also pins the active Reporium suite so a stale repo list
(the legacy ``repo-intelligence``/``forksync``/``portfolio`` entries)
cannot silently creep back in.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from reporium_audit.checks.workflows import (
    ACTIVE_SUITE_REPOS,
    SCHEDULED_WORKFLOWS,
    check_scheduled_workflows,
    check_workflows,
)


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


def test_legacy_repo_aliases_are_removed() -> None:
    for legacy in (
        "perditioinc/repo-intelligence",
        "perditioinc/forksync",
        "perditioinc/portfolio",
    ):
        assert legacy not in ACTIVE_SUITE_REPOS


def test_expanded_repos_includes_new_suite_members() -> None:
    """Regression: repo list must include ingestion, events, audit itself."""
    assert "perditioinc/reporium-ingestion" in ACTIVE_SUITE_REPOS
    assert "perditioinc/reporium-events" in ACTIVE_SUITE_REPOS
    assert "perditioinc/reporium-audit" in ACTIVE_SUITE_REPOS


@pytest.mark.asyncio
async def test_check_scheduled_workflows_skips_when_no_token():
    results = await check_scheduled_workflows("")
    assert len(results) == 1
    assert results[0]["status"] == "SKIP"


@pytest.mark.asyncio
@respx.mock
async def test_check_scheduled_workflows_flags_red_schedule():
    """A failing scheduled run produces FAIL for that row."""
    for repo, workflow_name in SCHEDULED_WORKFLOWS:
        respx.get(
            f"https://api.github.com/repos/{repo}/actions/runs"
        ).mock(
            return_value=httpx.Response(
                200,
                json={
                    "workflow_runs": [
                        {
                            "name": workflow_name,
                            "conclusion": (
                                "failure"
                                if workflow_name == "Data Quality Check"
                                else "success"
                            ),
                            "run_started_at": "2026-04-23T08:00:00Z",
                        }
                    ]
                },
            )
        )

    results = await check_scheduled_workflows("fake-token")
    by_name = {r["check"]: r for r in results}

    dqc = by_name["reporium-api schedule: Data Quality Check"]
    assert dqc["status"] == "FAIL"
    assert "failure" in dqc["detail"]

    nightly_sync = by_name["reporium-db schedule: Nightly Sync"]
    assert nightly_sync["status"] == "PASS"


@pytest.mark.asyncio
@respx.mock
async def test_check_scheduled_workflows_ignores_unrelated_run_names():
    """Latest scheduled run of a *different* workflow must not be used."""
    for repo, _ in SCHEDULED_WORKFLOWS:
        respx.get(
            f"https://api.github.com/repos/{repo}/actions/runs"
        ).mock(
            return_value=httpx.Response(
                200,
                json={
                    "workflow_runs": [
                        {
                            "name": "Some Other Workflow",
                            "conclusion": "success",
                            "run_started_at": "2026-04-23T08:00:00Z",
                        }
                    ]
                },
            )
        )

    results = await check_scheduled_workflows("fake-token")
    # No run matches by name, so the per-row status is WARN not PASS.
    assert all(r["status"] == "WARN" for r in results), results


@pytest.mark.asyncio
@respx.mock
async def test_check_workflows_returns_row_per_repo():
    for repo in ACTIVE_SUITE_REPOS:
        respx.get(
            f"https://api.github.com/repos/{repo}/actions/runs"
        ).mock(
            return_value=httpx.Response(
                200,
                json={
                    "workflow_runs": [
                        {"name": "CI", "conclusion": "success"}
                    ]
                },
            )
        )

    results = await check_workflows("fake-token")
    assert len(results) == len(ACTIVE_SUITE_REPOS)
    assert all(r["status"] == "PASS" for r in results)
