"""Check GitHub Actions workflow status for the Reporium suite.

Two distinct checks live here:

- ``check_workflows`` looks at the *latest* run per repo, regardless of
  trigger. Fast smoke test that a repo's CI surface is green overall.

- ``check_scheduled_workflows`` looks at the latest run *named after a
  specific scheduled workflow*. This is the layer that would have
  caught the 2026-04-23 Data Quality Check failures: the repo's
  latest run (a passing ``workflow_dispatch``) was green, so
  ``check_workflows`` reported PASS while the nightly scheduled run
  was red for days.

The latter deliberately filters by workflow *name* rather than the
``event=schedule`` query parameter because some workflows can be run
both manually and on cron; once the name matches we trust any
recent run of that workflow to reflect its current health.
"""

from __future__ import annotations

import httpx

REPOS = [
    "perditioinc/forksync",
    "perditioinc/reporium-db",
    "perditioinc/reporium-dataset",
    "perditioinc/portfolio",
    "perditioinc/reporium-roadmap",
    "perditioinc/reporium-metrics",
    "perditioinc/repo-intelligence",
    "perditioinc/reporium-api",
    # Added 2026-04-24: tracked repos that nightly jobs depend on.
    "perditioinc/reporium-ingestion",
    "perditioinc/reporium-events",
    "perditioinc/reporium-audit",
]


# ``(repo, workflow_name)`` pairs for scheduled jobs whose health
# cannot be inferred from the repo's "latest run" alone. Keep this
# list short and correct: every entry is one extra API call per audit
# run, and a wrong name silently becomes a WARN.
SCHEDULED_WORKFLOWS: list[tuple[str, str]] = [
    ("perditioinc/forksync", "Nightly Fork Sync"),
    ("perditioinc/reporium-db", "Nightly Sync"),
    ("perditioinc/reporium-ingestion", "Nightly Graph Build"),
    ("perditioinc/reporium-api", "Data Quality Check"),
]


async def check_workflows(token: str) -> list[dict]:
    """Check latest workflow run status for all tracked repos."""
    results: list[dict] = []
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        for repo in REPOS:
            try:
                r = await client.get(
                    f"https://api.github.com/repos/{repo}/actions/runs?per_page=1",
                    headers=headers,
                )
                runs = r.json().get("workflow_runs", [])
                if not runs:
                    results.append({
                        "check": f"{repo} workflows",
                        "status": "WARN",
                        "detail": "No runs",
                    })
                    continue
                latest = runs[0]
                conclusion = latest.get("conclusion", "unknown")
                name = latest.get("name", "unknown")
                passed = conclusion == "success"
                results.append({
                    "check": f"{repo.split('/')[1]} CI",
                    "status": "PASS" if passed else "FAIL",
                    "detail": f"{name}: {conclusion}",
                })
            except Exception as e:
                results.append({
                    "check": f"{repo} workflows",
                    "status": "FAIL",
                    "detail": str(e)[:100],
                })

    return results


async def check_scheduled_workflows(token: str) -> list[dict]:
    """Check each ``(repo, workflow_name)`` pair's latest matching run.

    For each entry in ``SCHEDULED_WORKFLOWS`` we fetch a recent page of
    workflow runs, filter by workflow name, and take the newest match.
    A FAIL there means the scheduled job itself is red -- even if the
    repo's overall "latest run" is green because of a more recent
    ``workflow_dispatch`` or unrelated CI event.

    When ``token`` is empty we emit a single ``SKIP`` -- this endpoint
    is rate-limited and the audit's GH_TOKEN is the standard way to
    access it.
    """
    if not token:
        return [{
            "check": "scheduled workflows",
            "status": "SKIP",
            "detail": "GH_TOKEN not set -- cannot query GitHub Actions API",
        }]

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    results: list[dict] = []
    async with httpx.AsyncClient(timeout=15) as client:
        for repo, workflow_name in SCHEDULED_WORKFLOWS:
            repo_short = repo.split("/", 1)[1]
            check_name = f"{repo_short} schedule: {workflow_name}"
            try:
                r = await client.get(
                    f"https://api.github.com/repos/{repo}/actions/runs?per_page=30",
                    headers=headers,
                )
            except Exception as e:
                results.append({
                    "check": check_name,
                    "status": "FAIL",
                    "detail": f"fetch error: {str(e)[:80]}",
                })
                continue

            if r.status_code != 200:
                results.append({
                    "check": check_name,
                    "status": "FAIL",
                    "detail": f"HTTP {r.status_code} from GitHub API",
                })
                continue

            runs = r.json().get("workflow_runs", []) or []
            match = next(
                (run for run in runs if (run.get("name") or "") == workflow_name),
                None,
            )
            if match is None:
                # No recent run for this specific workflow -- treat as
                # WARN, not PASS. The scheduled job may have been
                # renamed, disabled, or silently stopped triggering.
                results.append({
                    "check": check_name,
                    "status": "WARN",
                    "detail": "no recent run with matching workflow name",
                })
                continue

            conclusion = match.get("conclusion") or "pending"
            started = match.get("run_started_at") or match.get("created_at") or "?"
            passed = conclusion == "success"
            results.append({
                "check": check_name,
                "status": "PASS" if passed else "FAIL",
                "detail": f"{conclusion} (started {started})",
            })

    return results
