"""Regression test for the cron-masked-by-dispatch failure mode.

The documented 2026-04-23 incident: a repo's *latest* workflow run was a
green ``workflow_dispatch`` (someone re-ran CI manually), so the
latest-run-only smoke test (``check_workflows``) reported PASS -- while the
nightly scheduled run (``Data Quality Check``) had been red for days.

``check_scheduled_workflows`` exists precisely to catch this. This test
exercises the two checks against the SAME synthetic GitHub API payload and
asserts the contrast directly:

  - ``check_workflows`` -> PASS for reporium-api (sees only the latest run)
  - ``check_scheduled_workflows`` -> FAIL for the Data Quality Check row
    (filters by workflow name and finds the red scheduled run)

If the scheduled check ever regresses to "latest run only" it would also
go green here, and this test would fail -- which is the point.
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

# The repo whose scheduled job is red but whose latest run is a green
# manual dispatch. Pulled from the real config so the test tracks the
# actual (repo, workflow) pair the audit defends.
MASKED_REPO = "perditioinc/reporium-api"
MASKED_WORKFLOW = "Data Quality Check"


def _runs_payload_with_masked_cron(workflow_name: str) -> dict:
    """A workflow_runs page where:

    - index 0 is the NEWEST run: a passing ``workflow_dispatch`` of CI,
    - a later entry is the scheduled ``workflow_name`` run, and it FAILED.

    This is the exact shape that fools a latest-run-only check.
    """
    return {
        "workflow_runs": [
            {
                "name": "CI",
                "event": "workflow_dispatch",
                "conclusion": "success",
                "run_started_at": "2026-04-25T18:00:00Z",
            },
            {
                "name": "CI",
                "event": "push",
                "conclusion": "success",
                "run_started_at": "2026-04-25T12:00:00Z",
            },
            {
                "name": workflow_name,
                "event": "schedule",
                "conclusion": "failure",
                "run_started_at": "2026-04-23T06:00:00Z",
            },
        ]
    }


def _all_green_payload(workflow_name: str) -> dict:
    """A page whose scheduled run is green (for the non-masked repos)."""
    return {
        "workflow_runs": [
            {
                "name": workflow_name,
                "event": "schedule",
                "conclusion": "success",
                "run_started_at": "2026-04-25T06:00:00Z",
            }
        ]
    }


@pytest.mark.asyncio
@respx.mock
async def test_red_cron_masked_by_green_dispatch_is_caught():
    """The masked-cron scenario: latest-run check passes, scheduled check fails."""
    # Mock the scheduled-workflow endpoint (per_page=30) for each tracked
    # scheduled pair. Only reporium-api's Data Quality Check is masked-red.
    for repo, workflow_name in SCHEDULED_WORKFLOWS:
        if repo == MASKED_REPO and workflow_name == MASKED_WORKFLOW:
            payload = _runs_payload_with_masked_cron(workflow_name)
        else:
            payload = _all_green_payload(workflow_name)
        respx.get(
            f"https://api.github.com/repos/{repo}/actions/runs"
        ).mock(return_value=httpx.Response(200, json=payload))

    # Mock the latest-run smoke endpoint (per_page=1) for every repo. The
    # masked repo returns its newest run = the green dispatch.
    for repo in ACTIVE_SUITE_REPOS:
        if repo == MASKED_REPO:
            latest = _runs_payload_with_masked_cron(MASKED_WORKFLOW)
            latest = {"workflow_runs": latest["workflow_runs"][:1]}
        else:
            latest = {"workflow_runs": [{"name": "CI", "conclusion": "success"}]}
        respx.get(
            f"https://api.github.com/repos/{repo}/actions/runs",
            params={"per_page": "1"},
        ).mock(return_value=httpx.Response(200, json=latest))

    smoke = await check_workflows("fake-token")
    scheduled = await check_scheduled_workflows("fake-token")

    smoke_by_name = {r["check"]: r for r in smoke}
    sched_by_name = {r["check"]: r for r in scheduled}

    # The smoke test is fooled: reporium-api's latest run is the green dispatch.
    api_smoke = smoke_by_name["reporium-api CI"]
    assert api_smoke["status"] == "PASS", (
        f"latest-run smoke test should be masked green, got {api_smoke}"
    )

    # The scheduled check is NOT fooled: it finds the red Data Quality Check.
    api_sched = sched_by_name["reporium-api schedule: Data Quality Check"]
    assert api_sched["status"] == "FAIL", (
        f"scheduled check must catch the red cron behind the green dispatch, "
        f"got {api_sched}"
    )
    assert "failure" in api_sched["detail"]

    # And the contrast is real: the smoke test did NOT flag this repo as failing.
    assert api_smoke["status"] != api_sched["status"], (
        "the whole point is that the two checks disagree for the masked repo"
    )


@pytest.mark.asyncio
@respx.mock
async def test_scheduled_check_picks_newest_matching_run_not_first_entry():
    """Name-filter must select the scheduled run even when it is not index 0.

    Guards against a naive ``runs[0]`` implementation: the matching scheduled
    run is buried under newer, unrelated runs.
    """
    for repo, workflow_name in SCHEDULED_WORKFLOWS:
        respx.get(
            f"https://api.github.com/repos/{repo}/actions/runs"
        ).mock(
            return_value=httpx.Response(
                200,
                json={
                    "workflow_runs": [
                        {
                            "name": "Unrelated Manual Run",
                            "event": "workflow_dispatch",
                            "conclusion": "success",
                            "run_started_at": "2026-04-26T09:00:00Z",
                        },
                        {
                            "name": workflow_name,
                            "event": "schedule",
                            "conclusion": "failure",
                            "run_started_at": "2026-04-25T06:00:00Z",
                        },
                    ]
                },
            )
        )

    results = await check_scheduled_workflows("fake-token")
    # Every scheduled row resolves to its buried red run -> all FAIL.
    assert all(r["status"] == "FAIL" for r in results), results
    assert all("failure" in r["detail"] for r in results), results
