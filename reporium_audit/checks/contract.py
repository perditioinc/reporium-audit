"""Check that /library/full satisfies CONTRACT.md — no null required fields."""

from __future__ import annotations

import httpx


REQUIRED_FIELDS = [
    "name", "fullName", "description", "url", "stars", "forks",
]

ENRICHED_FIELDS = [
    "readmeSummary", "primaryCategory", "allCategories", "enrichedTags",
    "builders", "pmSkills", "industries", "aiDevSkills", "programmingLanguages",
    "commitStats", "languageBreakdown", "languagePercentages",
]


async def check_contract(api_url: str) -> list[dict]:
    """Validate every repo in /library/full against the data contract."""
    results = []
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            r = await client.get(f"{api_url}/library/full")
            if r.status_code != 200:
                results.append({
                    "check": "contract: /library/full reachable",
                    "status": "FAIL",
                    "detail": f"HTTP {r.status_code}",
                })
                return results

            data = r.json()
            repos = data.get("repos", [])

            # Check: no private repos.
            # Forks are intentionally part of the curated catalog (Reporium's
            # product surface is forks of upstream open-source repos), so they
            # are not a privacy violation. Only ``isPrivate=true`` is.
            private = [repo["name"] for repo in repos if repo.get("isPrivate")]
            results.append({
                "check": "contract: no private repos exposed",
                "status": "PASS" if len(private) == 0 else "FAIL",
                "detail": f"{len(repos)} repos, {len(private)} private" if private else f"{len(repos)} public repos",
            })

            # Check: no null required fields
            null_issues = []
            for repo in repos:
                for field in REQUIRED_FIELDS:
                    val = repo.get(field)
                    if val is None or val == "":
                        null_issues.append(f"{repo.get('name', '?')}.{field}")

            results.append({
                "check": "contract: no null required fields",
                "status": "PASS" if len(null_issues) == 0 else "FAIL",
                "detail": f"0 nulls" if not null_issues else f"{len(null_issues)} nulls: {null_issues[:5]}",
            })

            # Check: no null enriched fields (arrays should be [] not null)
            enriched_nulls = []
            for repo in repos:
                for field in ENRICHED_FIELDS:
                    val = repo.get(field)
                    if val is None:
                        enriched_nulls.append(f"{repo.get('name', '?')}.{field}")

            results.append({
                "check": "contract: no null enriched fields",
                "status": "PASS" if len(enriched_nulls) == 0 else "WARN",
                "detail": f"0 nulls" if not enriched_nulls else f"{len(enriched_nulls)} nulls: {enriched_nulls[:5]}",
            })

        except Exception as e:
            results.append({
                "check": "contract: /library/full validation",
                "status": "FAIL",
                "detail": str(e)[:100],
            })

    return results
