"""Tests for /library/full data-contract checks.

Pins the 2026-04-26 fix that stopped conflating ``isFork`` with
``isPrivate``. Reporium's curated catalog intentionally contains forks
of upstream open-source repos -- forks are the product, not a privacy
violation. Only ``isPrivate=true`` rows constitute a contract failure.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from reporium_audit.checks.contract import check_contract


API_URL = "https://api.example.test"
LIBRARY_FULL_URL = f"{API_URL}/library/full"


def _repo(name: str, *, is_fork: bool = False, is_private: bool = False) -> dict:
    return {
        "name": name,
        "fullName": f"perditioinc/{name}",
        "description": "x",
        "url": f"https://github.com/perditioinc/{name}",
        "stars": 1,
        "forks": 0,
        "isFork": is_fork,
        "isPrivate": is_private,
        # enriched fields populated to keep null-checks PASS
        "readmeSummary": "x",
        "primaryCategory": "ai",
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


def _privacy_row(results: list[dict]) -> dict:
    matches = [r for r in results if "private" in r["check"]]
    assert len(matches) == 1, f"expected exactly one privacy row, got {results}"
    return matches[0]


@pytest.mark.asyncio
@respx.mock
async def test_forks_alone_do_not_trigger_privacy_failure():
    """Regression: forks are the product surface, not a privacy violation."""
    repos = [_repo(f"fork-{i}", is_fork=True) for i in range(3)]
    respx.get(LIBRARY_FULL_URL).mock(
        return_value=httpx.Response(200, json={"repos": repos})
    )

    results = await check_contract(API_URL)

    row = _privacy_row(results)
    assert row["status"] == "PASS"
    assert "private" in row["check"]
    assert "fork" not in row["check"]


@pytest.mark.asyncio
@respx.mock
async def test_private_repo_triggers_failure():
    """Privacy check still catches genuine private exposure."""
    repos = [
        _repo("public-fork", is_fork=True),
        _repo("leaked", is_private=True),
    ]
    respx.get(LIBRARY_FULL_URL).mock(
        return_value=httpx.Response(200, json={"repos": repos})
    )

    results = await check_contract(API_URL)

    row = _privacy_row(results)
    assert row["status"] == "FAIL"
    assert "1 private" in row["detail"]


@pytest.mark.asyncio
@respx.mock
async def test_clean_public_originals_pass():
    """Mixed clean catalog with no private rows should PASS."""
    repos = [
        _repo("original-1"),
        _repo("fork-1", is_fork=True),
    ]
    respx.get(LIBRARY_FULL_URL).mock(
        return_value=httpx.Response(200, json={"repos": repos})
    )

    results = await check_contract(API_URL)

    row = _privacy_row(results)
    assert row["status"] == "PASS"
    assert "2 public repos" in row["detail"]
