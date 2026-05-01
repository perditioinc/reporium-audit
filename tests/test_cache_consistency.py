"""Tests for the cache-vs-DB consistency invariant.

Pins the regression caught by memory entry 4931 (2026-04-26): an admin
backfill writes the ``repos.primary_category`` column but the per-slug
``/repos/<slug>`` Redis cache is not invalidated, so the API serves a
junction snapshot that disagrees with the column for up to one TTL
window.

The invariant compares ``/library/full``'s ``dbCategory`` (raw column,
the closest thing the audit has to DB ground truth without Cloud SQL
private-IP access) against ``/repos/<slug>``'s ``categories`` array.
A mismatch is FAIL; an unsamplable corpus is SKIP; a clean sample is
PASS.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from reporium_audit.checks.cache_consistency import (
    DEFAULT_SAMPLE_SEED,
    check_cache_consistency,
)


API_URL = "https://api.example.test"
LIBRARY_FULL_URL = f"{API_URL}/library/full"


def _library_repo(name: str, *, primary_category: str | None, db_category: str | None) -> dict:
    """Shape mirrors the production /library/full response shape -- only
    the fields this check reads are populated."""
    return {
        "name": name,
        "primaryCategory": primary_category or "Uncategorized",
        "dbCategory": db_category,
        "allCategories": [primary_category] if primary_category else [],
    }


def _detail_response(slug: str, category_names: list[str], *, with_is_primary: bool = True) -> dict:
    """Shape mirrors /repos/<slug> -- ``categories`` is a list of dicts
    with ``category_name``/``is_primary``."""
    return {
        "name": slug,
        "owner": "perditioinc",
        "categories": [
            {
                "category_id": cn.lower().replace(" ", "-").replace("&", "and"),
                "category_name": cn,
                "is_primary": with_is_primary and i == 0,
            }
            for i, cn in enumerate(category_names)
        ],
        "allCategories": category_names,
    }


def _row(results: list[dict]) -> dict:
    """The check returns exactly one result row."""
    assert len(results) == 1, f"expected one result row, got {results}"
    return results[0]


@pytest.mark.asyncio
@respx.mock
async def test_pass_when_dbcategory_present_in_detail_categories():
    """Clean cache: every sampled repo's dbCategory is also in its
    /repos/<slug> junction array."""
    repos = [
        _library_repo(f"repo-{i}", primary_category="Dev Tools & Automation",
                      db_category="Dev Tools & Automation")
        for i in range(20)
    ]
    respx.get(LIBRARY_FULL_URL).mock(
        return_value=httpx.Response(200, json={"repos": repos})
    )
    for i in range(20):
        respx.get(f"{API_URL}/repos/repo-{i}").mock(
            return_value=httpx.Response(200, json=_detail_response(
                f"repo-{i}", ["Dev Tools & Automation"]
            ))
        )

    results = await check_cache_consistency(API_URL, sample_size=10)

    row = _row(results)
    assert row["status"] == "PASS", row
    assert "10/10" in row["detail"] or "10 sampled repos" in row["detail"]


@pytest.mark.asyncio
@respx.mock
async def test_fail_when_detail_categories_missing_dbcategory():
    """Stale cache: /library/full says dbCategory=AI Agents but the
    cached /repos/<slug> still shows the pre-backfill list."""
    repos = [
        _library_repo("stale-1", primary_category="AI Agents", db_category="AI Agents"),
        _library_repo("fresh-1", primary_category="RAG & Retrieval",
                      db_category="RAG & Retrieval"),
    ]
    respx.get(LIBRARY_FULL_URL).mock(
        return_value=httpx.Response(200, json={"repos": repos})
    )
    # stale-1: dbCategory="AI Agents" but cached detail says "Dev Tools"
    respx.get(f"{API_URL}/repos/stale-1").mock(
        return_value=httpx.Response(200, json=_detail_response(
            "stale-1", ["Dev Tools & Automation"]
        ))
    )
    # fresh-1: cache is consistent with dbCategory
    respx.get(f"{API_URL}/repos/fresh-1").mock(
        return_value=httpx.Response(200, json=_detail_response(
            "fresh-1", ["RAG & Retrieval"]
        ))
    )

    results = await check_cache_consistency(API_URL, sample_size=2, sample_seed=42)

    row = _row(results)
    assert row["status"] == "FAIL", row
    assert "stale-1" in row["detail"]


@pytest.mark.asyncio
@respx.mock
async def test_fail_when_detail_categories_empty_but_db_has_value():
    """The 2026-04-26 build-your-own-x case: /library/full has a
    primaryCategory derived from junction but /repos/<slug> returns
    categories=[]. dbCategory=None should SKIP (no ground truth) but
    a non-null dbCategory with empty detail list is the staleness FAIL."""
    repos = [
        _library_repo("empty-detail", primary_category="Dev Tools & Automation",
                      db_category="Dev Tools & Automation"),
    ]
    respx.get(LIBRARY_FULL_URL).mock(
        return_value=httpx.Response(200, json={"repos": repos})
    )
    respx.get(f"{API_URL}/repos/empty-detail").mock(
        return_value=httpx.Response(200, json=_detail_response("empty-detail", []))
    )

    results = await check_cache_consistency(API_URL, sample_size=5)

    row = _row(results)
    assert row["status"] == "FAIL", row
    assert "empty-detail" in row["detail"]


@pytest.mark.asyncio
@respx.mock
async def test_skip_when_no_repo_has_dbcategory():
    """Pre-backfill state: every repo has dbCategory=None so the audit
    has no DB-side ground truth to compare against. SKIP, not FAIL --
    this is a missing-credential / missing-data condition, not a bug."""
    repos = [
        _library_repo(f"unbackfilled-{i}", primary_category="Dev Tools & Automation",
                      db_category=None)
        for i in range(5)
    ]
    respx.get(LIBRARY_FULL_URL).mock(
        return_value=httpx.Response(200, json={"repos": repos})
    )

    results = await check_cache_consistency(API_URL, sample_size=10)

    row = _row(results)
    assert row["status"] == "SKIP", row
    assert "dbCategory" in row["detail"]


@pytest.mark.asyncio
@respx.mock
async def test_skip_when_library_full_returns_non_200():
    """/library/full reachability is the contract check's job; if it
    fails, this check defers (SKIP) rather than double-failing."""
    respx.get(LIBRARY_FULL_URL).mock(return_value=httpx.Response(503))

    results = await check_cache_consistency(API_URL)

    row = _row(results)
    assert row["status"] == "SKIP", row
    assert "503" in row["detail"]


@pytest.mark.asyncio
@respx.mock
async def test_skip_when_library_full_unreachable():
    """Network error (timeout, DNS) on /library/full also skips."""
    respx.get(LIBRARY_FULL_URL).mock(side_effect=httpx.ConnectError("dns"))

    results = await check_cache_consistency(API_URL)

    row = _row(results)
    assert row["status"] == "SKIP", row


@pytest.mark.asyncio
@respx.mock
async def test_skip_when_all_detail_requests_fail():
    """If we cannot reach /repos/<slug> at all, defer to /repos health
    check rather than spurious-failing this invariant."""
    repos = [
        _library_repo(f"r-{i}", primary_category="X", db_category="X")
        for i in range(3)
    ]
    respx.get(LIBRARY_FULL_URL).mock(
        return_value=httpx.Response(200, json={"repos": repos})
    )
    for i in range(3):
        respx.get(f"{API_URL}/repos/r-{i}").mock(return_value=httpx.Response(500))

    results = await check_cache_consistency(API_URL, sample_size=3)

    row = _row(results)
    assert row["status"] == "SKIP", row
    assert "cannot evaluate" in row["detail"]


@pytest.mark.asyncio
@respx.mock
async def test_default_seed_is_reproducible():
    """Same seed -> same sample order; the failure detail names the
    same offending slug across repeated runs (so flaky failures
    are reproducible)."""
    repos = [
        _library_repo(f"r-{i}", primary_category="A", db_category="A")
        for i in range(20)
    ]
    respx.get(LIBRARY_FULL_URL).mock(
        return_value=httpx.Response(200, json={"repos": repos})
    )
    # Make every detail mismatch so we get a populated FAIL detail.
    for i in range(20):
        respx.get(f"{API_URL}/repos/r-{i}").mock(
            return_value=httpx.Response(200, json=_detail_response(f"r-{i}", ["B"]))
        )

    first = await check_cache_consistency(API_URL, sample_size=5, sample_seed=DEFAULT_SAMPLE_SEED)
    second = await check_cache_consistency(API_URL, sample_size=5, sample_seed=DEFAULT_SAMPLE_SEED)

    assert first[0]["status"] == "FAIL"
    assert second[0]["status"] == "FAIL"
    assert first[0]["detail"] == second[0]["detail"]
