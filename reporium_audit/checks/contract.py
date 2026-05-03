"""Check that public repo surfaces (API + static artifact) satisfy the
privacy contract — no private repos exposed, AND every repo carries a
verifiable privacy field.

Two distinct failure modes, two distinct rows:
  - "privacy field present": every repo emits ``isPrivate`` (camelCase) OR
    ``is_private`` (snake_case). Missing field is FAIL — without a positive
    privacy signal we cannot prove the artifact is leak-free, and the
    2026-04-27 hippo-harvest-assignment incident surfaced for ~22 hours
    precisely because the prior check used ``repo.get("isPrivate")`` and
    silently treated missing as public.
  - "no private repos exposed": every repo whose privacy field is set
    must be ``False``. Forks are NOT a privacy violation (Reporium's
    catalog intentionally contains forks of upstream public repos — this
    was the 2026-04-26 conflation fix).

Two surfaces:
  - ``check_contract(api_url)`` — runs against the live ``/library/full``
    API endpoint.
  - ``check_static_artifact(url)`` — runs against the baked frontend
    artifact (e.g. ``https://reporium.com/data/library.json``), which can
    serve stale data even after the API is fixed.

Both surfaces share the same privacy gates so a leak is caught at every hop.
"""

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


def _classify_privacy(repo: dict) -> str:
    """Return one of ``"private"``, ``"public"``, or ``"missing"``.

    Recognizes both naming conventions emitted by reporium-api over time:
      - ``isPrivate`` (camelCase, frontend-facing)
      - ``is_private`` (snake_case, raw DB shape)

    Any positive private signal wins. Any explicit-public signal clears the
    repo. If neither field is present (or both are ``None``), classification
    is ``"missing"`` — the audit treats this as failure rather than
    silently defaulting to public.
    """
    if repo.get("isPrivate") is True or repo.get("is_private") is True:
        return "private"
    if repo.get("isPrivate") is False or repo.get("is_private") is False:
        return "public"
    return "missing"


def _privacy_rows(repos: list[dict], *, surface: str) -> list[dict]:
    """Return the two privacy gate rows for the given repo collection.

    ``surface`` is prepended to each ``check`` field as a label, e.g.
    ``"static artifact"`` for the frontend-artifact run vs. ``"contract"``
    for the API run. Operators reading the audit report can then
    distinguish where each failure was observed.
    """
    classifications = [(repo.get("name", "?"), _classify_privacy(repo)) for repo in repos]

    private_repos = [name for name, c in classifications if c == "private"]
    missing_field = [name for name, c in classifications if c == "missing"]
    total = len(repos)

    rows: list[dict] = []

    rows.append({
        "check": f"{surface}: privacy field present on every repo",
        "status": "PASS" if not missing_field else "FAIL",
        "detail": (
            f"all {total} repos carry isPrivate / is_private"
            if not missing_field
            else (
                f"{len(missing_field)}/{total} repos missing isPrivate AND is_private. "
                f"Sample: {missing_field[:5]}. "
                "Fix: API /library/full must emit isPrivate (or is_private) on every repo."
            )
        ),
    })

    rows.append({
        "check": f"{surface}: no private repos exposed",
        "status": "PASS" if not private_repos else "FAIL",
        "detail": (
            f"{total} repos checked, none private"
            if not private_repos
            else f"{total} repos, {len(private_repos)} private exposed: {private_repos[:5]}"
        ),
    })

    return rows


async def check_contract(api_url: str) -> list[dict]:
    """Validate every repo in /library/full against the data contract."""
    results: list[dict] = []
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

            # Two privacy gates: privacy field present + no private repos exposed.
            results.extend(_privacy_rows(repos, surface="contract"))

            # No null required fields.
            null_issues: list[str] = []
            for repo in repos:
                for field in REQUIRED_FIELDS:
                    val = repo.get(field)
                    if val is None or val == "":
                        null_issues.append(f"{repo.get('name', '?')}.{field}")

            results.append({
                "check": "contract: no null required fields",
                "status": "PASS" if len(null_issues) == 0 else "FAIL",
                "detail": "0 nulls" if not null_issues else f"{len(null_issues)} nulls: {null_issues[:5]}",
            })

            # No null enriched fields (arrays should be [] not null).
            enriched_nulls: list[str] = []
            for repo in repos:
                for field in ENRICHED_FIELDS:
                    val = repo.get(field)
                    if val is None:
                        enriched_nulls.append(f"{repo.get('name', '?')}.{field}")

            results.append({
                "check": "contract: no null enriched fields",
                "status": "PASS" if len(enriched_nulls) == 0 else "WARN",
                "detail": "0 nulls" if not enriched_nulls else f"{len(enriched_nulls)} nulls: {enriched_nulls[:5]}",
            })

        except Exception as e:
            results.append({
                "check": "contract: /library/full validation",
                "status": "FAIL",
                "detail": str(e)[:100],
            })

    return results


async def check_static_artifact(url: str) -> list[dict]:
    """Run the privacy contract against the baked frontend artifact at ``url``.

    The static artifact (e.g. ``https://reporium.com/data/library.json``)
    is a separate hop from the API. It can serve stale data even after the
    API is fixed and a row is corrected — the 2026-04-27 hippo incident
    persisted on the frontend artifact for ~22 hours after the row was
    flagged. Run this gate alongside ``check_contract`` so both surfaces
    are validated against the same privacy invariants.
    """
    results: list[dict] = []
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        try:
            r = await client.get(url)
            if r.status_code != 200:
                results.append({
                    "check": "static artifact: reachable",
                    "status": "FAIL",
                    "detail": f"HTTP {r.status_code} on {url}",
                })
                return results

            data = r.json()
            repos = data.get("repos", [])

            results.append({
                "check": "static artifact: reachable",
                "status": "PASS",
                "detail": f"{len(repos)} repos at {url}",
            })

            # Same privacy gates, prefixed so operators can tell which surface failed.
            results.extend(_privacy_rows(repos, surface="static artifact"))

        except Exception as e:
            results.append({
                "check": "static artifact: validation",
                "status": "FAIL",
                "detail": str(e)[:100],
            })

    return results
