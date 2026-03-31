"""Tests for contract audit checks."""

from __future__ import annotations

import httpx
import pytest
import respx

from reporium_audit.checks.contract import _validate_repos, check_contract


def _base_repo(**overrides):
    repo = {
        "name": "reporium-api",
        "fullName": "perditioinc/reporium-api",
        "description": "API service",
        "url": "https://github.com/perditioinc/reporium-api",
        "stars": 42,
        "forks": 3,
        "isPrivate": False,
        "readmeSummary": "",
        "primaryCategory": "",
        "allCategories": [],
        "enrichedTags": [],
        "builders": [],
        "pmSkills": [],
        "industries": [],
        "aiDevSkills": [],
        "programmingLanguages": [],
        "commitStats": {},
        "languageBreakdown": {},
        "languagePercentages": {},
    }
    repo.update(overrides)
    return repo


def test_validate_repos_allows_forks_but_blocks_private_repos():
    results = _validate_repos([
        _base_repo(name="openclaw", fullName="perditioinc/openclaw", isFork=True),
    ])

    private_check = next(r for r in results if r["check"] == "contract: no private repos exposed")
    assert private_check["status"] == "PASS"


def test_validate_repos_flags_identity_and_type_drift():
    results = _validate_repos([
        _base_repo(url="https://github.com/perditioinc/wrong", allCategories="agents"),
        _base_repo(name="reporium-api", fullName="anotherorg/reporium-api"),
        _base_repo(name="broken", fullName="broken", isPrivate=True),
    ])

    by_check = {result["check"]: result for result in results}
    assert by_check["contract: no private repos exposed"]["status"] == "FAIL"
    assert by_check["contract: fullName uses owner/name"]["status"] == "FAIL"
    assert by_check["contract: repo names are globally unique"]["status"] == "WARN"
    assert by_check["contract: repo URLs match fullName"]["status"] == "FAIL"
    assert by_check["contract: enriched field types are stable"]["status"] == "FAIL"


@pytest.mark.asyncio
@respx.mock
async def test_check_contract_reports_http_failures():
    respx.get("https://api.example.com/library/full").mock(
        return_value=httpx.Response(503, json={"detail": "down"})
    )

    results = await check_contract("https://api.example.com")
    assert results == [{
        "check": "contract: /library/full reachable",
        "status": "FAIL",
        "detail": "HTTP 503",
    }]


@pytest.mark.asyncio
@respx.mock
async def test_check_contract_validates_repo_payload():
    respx.get("https://api.example.com/library/full").mock(
        return_value=httpx.Response(200, json={"repos": [_base_repo(), _base_repo(name="dup", fullName="perditioinc/reporium-api")]})
    )

    results = await check_contract("https://api.example.com")
    duplicate_check = next(r for r in results if r["check"] == "contract: fullName values are unique")
    assert duplicate_check["status"] == "FAIL"
