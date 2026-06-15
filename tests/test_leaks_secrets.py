"""Tests for the secret-pattern extension to the leaks check.

Kept in its own file so the hardening lane's ``tests/test_leaks.py``
(which covers the original email-scan behavior) stays untouched.
"""

from __future__ import annotations

import pytest
import respx
from httpx import Response

from reporium_audit.checks.leaks import (
    _scan_for_secret_patterns,
    check_leaks,
)


def test_detects_github_classic_token():
    hits = _scan_for_secret_patterns(
        "deploy with ghp_1234567890abcdefghijklmnopqrstuvwxyzAA and go"
    )
    assert any(name == "github-token" for name, _ in hits)


def test_detects_github_fine_grained_pat():
    # Fine-grained PATs are long — pick a realistic body.
    body = "use github_pat_" + "A" * 60 + " here"
    hits = _scan_for_secret_patterns(body)
    assert any(name == "github-fine-grained-pat" for name, _ in hits)


def test_detects_aws_access_key():
    hits = _scan_for_secret_patterns("AWS key AKIAIOSFODNN7EXAMPLE in env")
    assert any(name == "aws-access-key" for name, _ in hits)


def test_detects_google_api_key():
    hits = _scan_for_secret_patterns(
        "key=AIzaSyA-1234567890abcdefghijklmnopqrstuv "
    )
    assert any(name == "google-api-key" for name, _ in hits)


def test_detects_slack_token():
    hits = _scan_for_secret_patterns("SLACK_BOT=xoxb-123-456-ABCDEFGH")
    assert any(name == "slack-token" for name, _ in hits)


def test_detects_pem_private_key_header():
    hits = _scan_for_secret_patterns(
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
    hits = _scan_for_secret_patterns(body)
    assert hits == []


def test_allowlist_suppresses_match(monkeypatch):
    monkeypatch.setenv("AUDIT_SECRET_ALLOWLIST", "REDACTED")
    body = "ghp_REDACTEDREDACTEDREDACTEDREDACTEDREDACTEDREDAC"
    # Without the allowlist this would be a classic token hit; with
    # it the shared literal substring suppresses.
    hits = _scan_for_secret_patterns(body)
    assert hits == []


@pytest.mark.asyncio
async def test_check_leaks_reports_secret_fail_separately():
    """A repo with an embedded token must surface as a separate FAIL
    result, even if the email scan is clean."""
    repo = "perditioinc/fixture-repo"
    router = respx.mock(assert_all_called=False)
    router.get(
        f"https://raw.githubusercontent.com/{repo}/main/README.md"
    ).mock(
        return_value=Response(
            200,
            text=(
                "# Fixture\n"
                "All emails look fine: ops@perditio.com\n"
                "But this key leaked: AKIAIOSFODNN7EXAMPLE\n"
            ),
        )
    )
    with router:
        results = await check_leaks(repos=[repo])

    by_check = {r["check"]: r for r in results}

    email_check = by_check[f"leaks: {repo} README"]
    secret_check = by_check[f"leaks: {repo} README secrets"]

    assert email_check["status"] == "PASS"
    assert secret_check["status"] == "FAIL"
    # Detail must not echo the full key value.
    assert "AKIAIOSFODNN7EXAMPLE" not in secret_check["detail"]
    assert "aws-access-key" in secret_check["detail"]
