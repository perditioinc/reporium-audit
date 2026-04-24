"""Tests for the README secret-pattern check (``checks.secrets``).

Kept separate from the hardening lane's ``tests/test_leaks.py`` so the
two checks (email allowlist vs structured secret patterns) evolve
independently.
"""

from __future__ import annotations

import pytest
import respx
from httpx import Response

from reporium_audit.checks.secrets import (
    check_readme_secrets,
    scan_for_secret_patterns,
)


# ---------- pattern unit tests ----------


def test_detects_github_classic_token():
    hits = scan_for_secret_patterns(
        "deploy with ghp_1234567890abcdefghijklmnopqrstuvwxyzAA and go"
    )
    assert any(name == "github-token" for name, _ in hits)


def test_detects_github_fine_grained_pat():
    body = "use github_pat_" + "A" * 60 + " here"
    hits = scan_for_secret_patterns(body)
    assert any(name == "github-fine-grained-pat" for name, _ in hits)


def test_detects_aws_access_key():
    hits = scan_for_secret_patterns("AWS key AKIAIOSFODNN7EXAMPLE in env")
    assert any(name == "aws-access-key" for name, _ in hits)


def test_detects_google_api_key():
    # Google API keys are exactly 39 chars: ``AIza`` + 35.
    body = "key=AIza" + ("A" * 35) + " "
    hits = scan_for_secret_patterns(body)
    assert any(name == "google-api-key" for name, _ in hits)


def test_detects_slack_token():
    hits = scan_for_secret_patterns("SLACK_BOT=xoxb-123-456-ABCDEFGH")
    assert any(name == "slack-token" for name, _ in hits)


def test_detects_pem_private_key_header():
    hits = scan_for_secret_patterns(
        "-----BEGIN RSA PRIVATE KEY-----\nMIIE...\n-----END RSA PRIVATE KEY-----"
    )
    assert any(name == "private-key-pem" for name, _ in hits)


def test_ignores_prose_mentions():
    # These look secret-y but don't match the structured patterns.
    body = (
        "We rotate ghp_ tokens quarterly. "
        "Set AIza... in .env. "
        "The AKIA prefix marks access keys."
    )
    assert scan_for_secret_patterns(body) == []


def test_allowlist_suppresses_match(monkeypatch):
    monkeypatch.setenv("AUDIT_SECRET_ALLOWLIST", "REDACTED")
    # Without the allowlist this would be a classic token hit; with
    # it the shared literal substring suppresses.
    body = "ghp_REDACTEDREDACTEDREDACTEDREDACTEDREDACTED"
    assert scan_for_secret_patterns(body) == []


# ---------- end-to-end check behavior ----------


@pytest.mark.asyncio
async def test_check_flags_embedded_key_as_fail():
    repo = "perditioinc/fixture-repo"
    router = respx.mock(assert_all_called=False)
    router.get(
        f"https://raw.githubusercontent.com/{repo}/main/README.md"
    ).mock(
        return_value=Response(
            200,
            text=(
                "# Fixture\n"
                "Nothing to see here.\n"
                "But this leaked: AKIAIOSFODNN7EXAMPLE\n"
            ),
        )
    )
    with router:
        results = await check_readme_secrets(repos=[repo])

    assert len(results) == 1
    r = results[0]
    assert r["status"] == "FAIL"
    assert r["check"] == f"secrets: {repo} README"
    # The report must not rebroadcast the full secret value.
    assert "AKIAIOSFODNN7EXAMPLE" not in r["detail"]
    assert "aws-access-key" in r["detail"]


@pytest.mark.asyncio
async def test_check_passes_clean_readme():
    repo = "perditioinc/fixture-clean"
    router = respx.mock(assert_all_called=False)
    router.get(
        f"https://raw.githubusercontent.com/{repo}/main/README.md"
    ).mock(
        return_value=Response(200, text="# Fixture\nHello world.\n"),
    )
    with router:
        results = await check_readme_secrets(repos=[repo])
    assert results[0]["status"] == "PASS"


@pytest.mark.asyncio
async def test_check_warns_when_readme_missing():
    repo = "perditioinc/fixture-missing"
    router = respx.mock(assert_all_called=False)
    router.get(
        f"https://raw.githubusercontent.com/{repo}/main/README.md"
    ).mock(return_value=Response(404))
    router.get(
        f"https://raw.githubusercontent.com/{repo}/master/README.md"
    ).mock(return_value=Response(404))
    with router:
        results = await check_readme_secrets(repos=[repo])
    # Missing README isn't a failure — it's an observation; surface as
    # WARN so it's visible in the report without reddening the whole
    # area.
    assert results[0]["status"] == "WARN"
