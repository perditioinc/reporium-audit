"""Check reporium-db index.json is fresh and has real data."""

from __future__ import annotations

from datetime import datetime, timezone

import httpx

DB_INDEX_URL = "https://raw.githubusercontent.com/perditioinc/reporium-db/main/data/index.json"


async def check_reporium_db(token: str) -> list[dict]:
    """Check reporium-db data freshness and validity."""
    results = []
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            headers = {"Authorization": f"Bearer {token}"} if token else {}
            r = await client.get(DB_INDEX_URL, headers=headers)
            r.raise_for_status()
            data = r.json()

        meta = data.get("meta", {})
        total = meta.get("total", 0)
        last_updated = meta.get("last_updated", "")

        # Check total is reasonable
        results.append({
            "check": "reporium-db repo count",
            "status": "PASS" if total > 100 else "FAIL",
            "detail": f"{total} repos",
        })

        # Check freshness (< 25 hours)
        if last_updated:
            updated_dt = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
            hours_ago = (datetime.now(timezone.utc) - updated_dt).total_seconds() / 3600
            fresh = hours_ago < 25
            results.append({
                "check": "reporium-db index.json fresh",
                "status": "PASS" if fresh else "FAIL",
                "detail": f"Updated {hours_ago:.1f}h ago",
            })
        else:
            results.append({
                "check": "reporium-db index.json fresh",
                "status": "FAIL",
                "detail": "No last_updated field",
            })

    except Exception as e:
        results.append({"check": "reporium-db index.json", "status": "FAIL", "detail": str(e)[:100]})

    return results
