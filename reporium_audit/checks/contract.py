"""Check that /library/full satisfies the public payload contract."""

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

LIST_FIELDS = [
    "allCategories",
    "enrichedTags",
    "builders",
    "pmSkills",
    "industries",
    "aiDevSkills",
    "programmingLanguages",
]

DICT_FIELDS = [
    "commitStats",
    "languageBreakdown",
    "languagePercentages",
]


def _repo_label(repo: dict) -> str:
    """Return the most useful repo identifier available for audit messages."""
    return repo.get("fullName") or repo.get("name") or "?"


def _validate_repos(repos: list[dict]) -> list[dict]:
    """Validate repo payloads for nulls, identity drift, and type drift."""
    results: list[dict] = []

    private = [repo.get("fullName") or repo.get("name", "?") for repo in repos if repo.get("isPrivate")]
    results.append({
        "check": "contract: no private repos exposed",
        "status": "PASS" if not private else "FAIL",
        "detail": f"{len(repos)} public repos" if not private else f"{len(private)} private repos: {private[:5]}",
    })

    null_issues = []
    for repo in repos:
        for field in REQUIRED_FIELDS:
            val = repo.get(field)
            if val is None or val == "":
                null_issues.append(f"{_repo_label(repo)}.{field}")

    results.append({
        "check": "contract: no null required fields",
        "status": "PASS" if not null_issues else "FAIL",
        "detail": "0 nulls" if not null_issues else f"{len(null_issues)} nulls: {null_issues[:5]}",
    })

    enriched_nulls = []
    for repo in repos:
        for field in ENRICHED_FIELDS:
            if repo.get(field) is None:
                enriched_nulls.append(f"{_repo_label(repo)}.{field}")

    results.append({
        "check": "contract: no null enriched fields",
        "status": "PASS" if not enriched_nulls else "WARN",
        "detail": "0 nulls" if not enriched_nulls else f"{len(enriched_nulls)} nulls: {enriched_nulls[:5]}",
    })

    malformed_full_names = []
    duplicate_full_names = set()
    seen_full_names = set()
    name_collisions: dict[str, set[str]] = {}
    url_mismatches = []
    type_issues = []

    for repo in repos:
        label = _repo_label(repo)
        full_name = repo.get("fullName")
        name = repo.get("name")
        url = repo.get("url", "")

        if not isinstance(full_name, str) or full_name.count("/") != 1:
            malformed_full_names.append(label)
        else:
            if full_name in seen_full_names:
                duplicate_full_names.add(full_name)
            seen_full_names.add(full_name)

        if isinstance(name, str) and isinstance(full_name, str):
            name_collisions.setdefault(name, set()).add(full_name)

        if isinstance(url, str) and isinstance(full_name, str) and full_name and not url.rstrip("/").endswith(full_name):
            url_mismatches.append(label)

        for field in LIST_FIELDS:
            value = repo.get(field)
            if value is not None and not isinstance(value, list):
                type_issues.append(f"{label}.{field}={type(value).__name__}")

        for field in DICT_FIELDS:
            value = repo.get(field)
            if value is not None and not isinstance(value, dict):
                type_issues.append(f"{label}.{field}={type(value).__name__}")

    results.append({
        "check": "contract: fullName uses owner/name",
        "status": "PASS" if not malformed_full_names else "FAIL",
        "detail": "All repos have owner/name fullName" if not malformed_full_names else f"{len(malformed_full_names)} malformed: {malformed_full_names[:5]}",
    })

    collisions = sorted(name for name, full_names in name_collisions.items() if len(full_names) > 1)
    results.append({
        "check": "contract: repo names are globally unique",
        "status": "WARN" if collisions else "PASS",
        "detail": "No name collisions" if not collisions else f"{len(collisions)} collisions: {collisions[:5]}",
    })

    results.append({
        "check": "contract: fullName values are unique",
        "status": "PASS" if not duplicate_full_names else "FAIL",
        "detail": "No duplicate fullName values" if not duplicate_full_names else f"{len(duplicate_full_names)} duplicates: {sorted(duplicate_full_names)[:5]}",
    })

    results.append({
        "check": "contract: repo URLs match fullName",
        "status": "PASS" if not url_mismatches else "FAIL",
        "detail": "All repo URLs align with fullName" if not url_mismatches else f"{len(url_mismatches)} mismatches: {url_mismatches[:5]}",
    })

    results.append({
        "check": "contract: enriched field types are stable",
        "status": "PASS" if not type_issues else "FAIL",
        "detail": "No type drift detected" if not type_issues else f"{len(type_issues)} type issues: {type_issues[:5]}",
    })

    return results


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
            results.extend(_validate_repos(repos))

        except Exception as e:
            results.append({
                "check": "contract: /library/full validation",
                "status": "FAIL",
                "detail": str(e)[:100],
            })

    return results
