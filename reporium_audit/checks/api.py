"""Check reporium-api is responding with valid data."""

from __future__ import annotations

import httpx


async def check_api(api_url: str) -> list[dict]:
    """Run all API health checks. Returns list of check results."""
    results = []
    async with httpx.AsyncClient(timeout=15) as client:
        # /health
        try:
            r = await client.get(f"{api_url}/health")
            data = r.json()
            passed = r.status_code == 200 and data.get("status") == "ok"
            results.append({
                "check": "reporium-api /health",
                "status": "PASS" if passed else "FAIL",
                "detail": str(data)[:100],
            })
        except Exception as e:
            results.append({"check": "reporium-api /health", "status": "FAIL", "detail": str(e)[:100]})

        # /repos
        try:
            r = await client.get(f"{api_url}/repos?limit=1")
            data = r.json()
            total = data.get("total", 0)
            passed = r.status_code == 200 and total > 0
            results.append({
                "check": "reporium-api /repos",
                "status": "PASS" if passed else "FAIL",
                "detail": f"{total} repos",
            })
        except Exception as e:
            results.append({"check": "reporium-api /repos", "status": "FAIL", "detail": str(e)[:100]})

        # /search
        try:
            r = await client.get(f"{api_url}/search?q=python")
            data = r.json()
            passed = r.status_code == 200 and len(data) > 0
            results.append({
                "check": "reporium-api /search",
                "status": "PASS" if passed else "FAIL",
                "detail": f"{len(data)} results",
            })
        except Exception as e:
            results.append({"check": "reporium-api /search", "status": "FAIL", "detail": str(e)[:100]})

    return results
