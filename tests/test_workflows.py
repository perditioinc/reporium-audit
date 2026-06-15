"""Tests for scheduled-workflow gating.

Uses respx to mock GitHub Actions API responses and verifies that the
check correctly distinguishes a green ``workflow_dispatch`` run from a
red scheduled run — the pattern behind the 2026-04-23 Data Quality Check
misses.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from reporium_audit.checks.workflows import (
    SCHEDULED_WORKFLOWS,
    check_scheduled_workflows,
    check_workflows,
)


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

    fork_sync = by_name["forksync schedule: Nightly Fork Sync"]
    assert fork_sync["status"] == "PASS"


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
    from reporium_audit.checks.workflows import REPOS

    for repo in REPOS:
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
    assert len(results) == len(REPOS)
    assert all(r["status"] == "PASS" for r in results)


def test_expanded_repos_includes_new_suite_members():
    """Regression: repo list must include ingestion, events, audit itself."""
    from reporium_audit.checks.workflows import REPOS

    assert "perditioinc/reporium-ingestion" in REPOS
    assert "perditioinc/reporium-events" in REPOS
    assert "perditioinc/reporium-audit" in REPOS
