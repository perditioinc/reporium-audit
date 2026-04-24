"""Tests for cross-source suite drift detection."""

from __future__ import annotations

import pytest
import respx
from httpx import Response

from reporium_audit.checks.drift import (
    DB_INDEX_URL,
    _classify_drift,
    check_suite_drift,
)

API_URL = "https://reporium-api.example"


def _fixture(api_repos, library_len, db_total):
    """Build a respx router preloaded with the three sources."""
    router = respx.mock(assert_all_called=False)
    router.get(f"{API_URL}/repos").mock(
        return_value=Response(200, json={"total": api_repos})
    )
    router.get(f"{API_URL}/library/full").mock(
        return_value=Response(
            200,
            json={"repos": [{"name": f"r{i}"} for i in range(library_len)]},
        )
    )
    router.get(DB_INDEX_URL).mock(
        return_value=Response(200, json={"meta": {"total": db_total}})
    )
    return router


@pytest.mark.asyncio
async def test_drift_pass_when_counts_match():
    with _fixture(api_repos=826, library_len=826, db_total=826):
        results = await check_suite_drift(API_URL)
    assert len(results) == 1
    assert results[0]["status"] == "PASS"
    assert "826" in results[0]["detail"]


@pytest.mark.asyncio
async def test_drift_pass_on_noise_delta():
    # 1-repo delta is below MIN_ABSOLUTE_DELTA — never a finding.
    with _fixture(api_repos=826, library_len=825, db_total=826):
        results = await check_suite_drift(API_URL)
    assert results[0]["status"] == "PASS"


@pytest.mark.asyncio
async def test_drift_warn_small_delta():
    # 3-repo delta on 200 total = 1.5% — above warn threshold (1%),
    # below fail threshold (5%).
    with _fixture(api_repos=200, library_len=200, db_total=197):
        results = await check_suite_drift(API_URL)
    assert results[0]["status"] == "WARN", results[0]


@pytest.mark.asyncio
async def test_drift_fail_large_delta():
    # Half the repos vanished from /repos — classic silent loss.
    with _fixture(api_repos=400, library_len=820, db_total=826):
        results = await check_suite_drift(API_URL)
    assert results[0]["status"] == "FAIL"
    detail = results[0]["detail"]
    assert "400" in detail and "826" in detail


@pytest.mark.asyncio
async def test_drift_warn_when_only_one_source_reachable():
    router = respx.mock(assert_all_called=False)
    router.get(f"{API_URL}/repos").mock(return_value=Response(500))
    router.get(f"{API_URL}/library/full").mock(return_value=Response(500))
    router.get(DB_INDEX_URL).mock(
        return_value=Response(200, json={"meta": {"total": 826}})
    )
    with router:
        results = await check_suite_drift(API_URL)
    assert results[0]["status"] == "WARN"
    assert "Not enough reachable sources" in results[0]["detail"]


@pytest.mark.asyncio
async def test_drift_skips_when_api_url_missing():
    results = await check_suite_drift("")
    assert results[0]["status"] == "SKIP"


def test_classify_all_zero_is_fail():
    status, detail = _classify_drift(
        {"a": 0, "b": 0, "c": 0}, warn_pct=0.01, fail_pct=0.05
    )
    assert status == "FAIL"
    assert "0 repos" in detail


def test_classify_threshold_edges():
    # 10% delta — above fail threshold.
    status, _ = _classify_drift(
        {"a": 900, "b": 1000}, warn_pct=0.01, fail_pct=0.05
    )
    assert status == "FAIL"
    # 2% delta — between warn and fail.
    status, _ = _classify_drift(
        {"a": 980, "b": 1000}, warn_pct=0.01, fail_pct=0.05
    )
    assert status == "WARN"
    # 0.1% delta — below warn.
    status, _ = _classify_drift(
        {"a": 999, "b": 1000}, warn_pct=0.01, fail_pct=0.05
    )
    assert status == "PASS"
