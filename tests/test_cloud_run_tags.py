"""Tests for the Cloud Run candidate-tag leak probe.

The real check harvests tag names from recent GitHub workflow runs and
then probes the Cloud Run tagged URL pattern. We mock both to verify
that a tagged revision differing from production is flagged, while a
matching or unreachable tag doesn't trigger a false positive.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from reporium_audit.checks.cloud_run_tags import (
    CANDIDATE_TAG_RE,
    _extract_revision,
    _tagged_url,
    check_cloud_run_tags,
)


def test_candidate_tag_regex_matches_common_forms():
    assert CANDIDATE_TAG_RE.findall(
        "Deploy candidate-abc123 to staging"
    ) == ["candidate-abc123"]
    assert CANDIDATE_TAG_RE.findall(
        "tags: candidate-feat-xyz, candidate-042"
    ) == ["candidate-feat-xyz", "candidate-042"]


def test_tagged_url_builds_cloud_run_format():
    url = _tagged_url(
        "https://reporium-api-573778300586.us-central1.run.app",
        "candidate-abc",
    )
    assert url == (
        "https://candidate-abc---reporium-api-573778300586"
        ".us-central1.run.app/health"
    )


def test_tagged_url_strips_existing_tag():
    url = _tagged_url(
        "https://old-tag---reporium-api-573778300586.us-central1.run.app",
        "candidate-xyz",
    )
    assert "old-tag---" not in url
    assert "candidate-xyz---reporium-api-573778300586" in url


def test_extract_revision_tries_common_keys():
    assert _extract_revision({"revision": "r1"}) == "r1"
    assert _extract_revision({"k_revision": "r2"}) == "r2"
    assert _extract_revision({"git_sha": "abc"}) == "abc"
    assert _extract_revision({}) is None
    assert _extract_revision(None) is None


@pytest.mark.asyncio
async def test_check_cloud_run_tags_skips_without_token():
    results = await check_cloud_run_tags("https://api.example.com", "")
    assert results[0]["status"] == "SKIP"


@pytest.mark.asyncio
async def test_check_cloud_run_tags_skips_without_url():
    results = await check_cloud_run_tags("", "fake")
    assert results[0]["status"] == "SKIP"


@pytest.mark.asyncio
@respx.mock
async def test_check_cloud_run_tags_no_harvested_tags_is_pass():
    api_url = "https://reporium-api-573778300586.us-central1.run.app"
    respx.get(f"{api_url}/health").mock(
        return_value=httpx.Response(200, json={"revision": "prod-rev"})
    )
    respx.get(
        "https://api.github.com/repos/perditioinc/reporium-api/actions/runs"
    ).mock(
        return_value=httpx.Response(
            200,
            json={"workflow_runs": [{"name": "Deploy", "display_title": "feat"}]},
        )
    )

    results = await check_cloud_run_tags(api_url, "fake-token")
    assert results[0]["status"] == "PASS"
    assert "No candidate tags" in results[0]["detail"]


@pytest.mark.asyncio
@respx.mock
async def test_check_cloud_run_tags_flags_stale_tag():
    api_url = "https://reporium-api-573778300586.us-central1.run.app"
    respx.get(f"{api_url}/health").mock(
        return_value=httpx.Response(200, json={"revision": "prod-rev"})
    )
    respx.get(
        "https://api.github.com/repos/perditioinc/reporium-api/actions/runs"
    ).mock(
        return_value=httpx.Response(
            200,
            json={
                "workflow_runs": [
                    {
                        "name": "Deploy to Cloud Run",
                        "display_title": "candidate-abc",
                        "head_branch": "main",
                    }
                ]
            },
        )
    )
    respx.get(
        "https://candidate-abc---reporium-api-573778300586"
        ".us-central1.run.app/health"
    ).mock(return_value=httpx.Response(200, json={"revision": "stale-rev"}))

    results = await check_cloud_run_tags(api_url, "fake-token")
    tag_row = next(r for r in results if r["check"] == "cloud run candidate tags")
    assert tag_row["status"] == "FAIL"
    assert "candidate-abc" in tag_row["detail"]


@pytest.mark.asyncio
@respx.mock
async def test_check_cloud_run_tags_matching_revision_is_pass():
    api_url = "https://reporium-api-573778300586.us-central1.run.app"
    respx.get(f"{api_url}/health").mock(
        return_value=httpx.Response(200, json={"revision": "shared-rev"})
    )
    respx.get(
        "https://api.github.com/repos/perditioinc/reporium-api/actions/runs"
    ).mock(
        return_value=httpx.Response(
            200,
            json={
                "workflow_runs": [
                    {
                        "name": "Deploy to Cloud Run",
                        "display_title": "candidate-same",
                    }
                ]
            },
        )
    )
    respx.get(
        "https://candidate-same---reporium-api-573778300586"
        ".us-central1.run.app/health"
    ).mock(return_value=httpx.Response(200, json={"revision": "shared-rev"}))

    results = await check_cloud_run_tags(api_url, "fake-token")
    tag_row = next(r for r in results if r["check"] == "cloud run candidate tags")
    assert tag_row["status"] == "PASS"
    assert "same-as-prod=1" in tag_row["detail"]
