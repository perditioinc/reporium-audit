"""Check all GitHub Actions workflows pass/fail status."""

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
