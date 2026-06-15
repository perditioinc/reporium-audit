"""Check GitHub Actions workflow status across the Reporium suite.

Two complementary checks are exposed:

- ``check_workflows``: latest run per repo (legacy behaviour).
- ``check_scheduled_workflows``: latest *scheduled* run for a curated
  list of (repo, workflow_name). Catches the case where a manual
  ``workflow_dispatch`` run is green while the cron schedule is red — the
  pattern behind the 2026-04-23 Data Quality Check misses.
"""

from __future__ import annotations

import httpx

# Latest-run-per-repo check. Expanded 2026-04-24 to include the three
# repos that have joined the active suite since the audit was first
# written (ingestion, events, audit itself).
REPOS = [
    "perditioinc/forksync",
    "perditioinc/reporium-db",
    "perditioinc/reporium-dataset",
    "perditioinc/portfolio",
    "perditioinc/reporium-roadmap",
    "perditioinc/reporium-metrics",
    "perditioinc/repo-intelligence",
    "perditioinc/reporium-api",
    "perditioinc/reporium-ingestion",
    "perditioinc/reporium-events",
    "perditioinc/reporium-audit",
]

# Scheduled-workflow gating. A workflow_dispatch run can mask a broken
# cron, so for the jobs we actually rely on nightly we pin the check to
# ``event=schedule``.
SCHEDULED_WORKFLOWS: list[tuple[str, str]] = [
    ("perditioinc/forksync", "Nightly Fork Sync"),
    ("perditioinc/reporium-db", "Nightly Sync"),
    ("perditioinc/reporium-dataset", "Nightly README Update"),
    ("perditioinc/portfolio", "Nightly Portfolio Update"),
    ("perditioinc/reporium-roadmap", "Nightly Roadmap Update"),
    ("perditioinc/reporium-metrics", "Nightly Metrics Collection"),
    ("perditioinc/reporium-api", "Data Quality Check"),
    ("perditioinc/reporium-ingestion", "Nightly Graph Build"),
]


async def check_workflows(token: str) -> list[dict]:
    """Check latest workflow run status for all tracked repos."""
    results = []
    async with httpx.AsyncClient(timeout=15) as client:
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"}
        for repo in REPOS:
            try:
                r = await client.get(
                    f"https://api.github.com/repos/{repo}/actions/runs?per_page=1",
                    headers=headers,
                )
                runs = r.json().get("workflow_runs", [])
                if not runs:
                    results.append({"check": f"{repo} workflows", "status": "WARN", "detail": "No runs"})
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
                results.append({"check": f"{repo} workflows", "status": "FAIL", "detail": str(e)[:100]})

    return results


async def check_scheduled_workflows(token: str) -> list[dict]:
    """Verify the most recent *scheduled* run succeeded for each tracked job.

    ``check_workflows`` looks at the latest run of any type, so a manual
    ``workflow_dispatch`` success can mask a cron job that has been
    failing for days. This check filters on ``event=schedule`` so a
    red schedule surfaces immediately.
    """
    results: list[dict] = []

    if not token:
        results.append({
            "check": "scheduled workflows",
            "status": "SKIP",
            "detail": "GH_TOKEN not set",
        })
        return results

    async with httpx.AsyncClient(timeout=15) as client:
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
        }
        for repo, workflow_name in SCHEDULED_WORKFLOWS:
            check_name = f"{repo.split('/')[1]} schedule: {workflow_name}"
            try:
                r = await client.get(
                    f"https://api.github.com/repos/{repo}/actions/runs"
                    f"?event=schedule&per_page=1",
                    headers=headers,
                )
                if r.status_code != 200:
                    results.append({
                        "check": check_name,
                        "status": "FAIL",
                        "detail": f"HTTP {r.status_code}",
                    })
                    continue

                # Filter client-side by workflow name — GitHub's ``name``
                # query param only works with a workflow file path.
                runs = [
                    run for run in r.json().get("workflow_runs", [])
                    if run.get("name") == workflow_name
                ]

                if not runs:
                    # Widen the lookback a little before deciding this is
                    # WARN vs FAIL — a brand-new workflow may not have a
                    # scheduled run yet.
                    r2 = await client.get(
                        f"https://api.github.com/repos/{repo}/actions/runs"
                        f"?event=schedule&per_page=20",
                        headers=headers,
                    )
                    runs = [
                        run for run in r2.json().get("workflow_runs", [])
                        if run.get("name") == workflow_name
                    ]

                if not runs:
                    results.append({
                        "check": check_name,
                        "status": "WARN",
                        "detail": "No scheduled runs found in last 20",
                    })
                    continue

                latest = runs[0]
                conclusion = latest.get("conclusion", "unknown")
                results.append({
                    "check": check_name,
                    "status": "PASS" if conclusion == "success" else "FAIL",
                    "detail": f"{conclusion} @ {latest.get('run_started_at', '?')}",
                })
            except Exception as e:
                results.append({
                    "check": check_name,
                    "status": "FAIL",
                    "detail": str(e)[:100],
                })

    return results
