"""Tests for public-README PII leak check.

Covers the 2026-04-16 regression signal: a personal email address
leaking into a public README. We pin the allowlist semantics and the
env-var override here so that behaviour doesn't quietly drift.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from reporium_audit.checks.leaks import (
    DEFAULT_ALLOWED_DOMAINS,
    _allowed_domains,
    _scan_for_forbidden_emails,
    check_leaks,
)


def test_scan_allows_trusted_domains():
    text = "Reach out at ops@perditio.com for help."
    assert _scan_for_forbidden_emails(text, DEFAULT_ALLOWED_DOMAINS) == []


def test_scan_flags_untrusted_domain():
    text = "Contact me at someone@gmail.com."
    hits = _scan_for_forbidden_emails(text, DEFAULT_ALLOWED_DOMAINS)
    assert hits == ["someone@gmail.com"]


def test_scan_allows_github_noreply():
    text = "12345+someone@users.noreply.github.com"
    assert _scan_for_forbidden_emails(text, DEFAULT_ALLOWED_DOMAINS) == []


def test_scan_allows_subdomain_of_allowed():
    text = "ops@mail.perditio.com"
    # Subdomains of allowed domains are themselves allowed.
    assert _scan_for_forbidden_emails(text, DEFAULT_ALLOWED_DOMAINS) == []


def test_allowed_domains_env_override(monkeypatch):
    monkeypatch.setenv("AUDIT_ALLOWED_EMAIL_DOMAINS", "example.com , foo.org")
    domains = _allowed_domains()
    assert "example.com" in domains
    assert "foo.org" in domains
    assert "perditio.com" in domains  # defaults still present


@pytest.mark.asyncio
@respx.mock
async def test_check_leaks_flags_forbidden_email():
    repo = "perditioinc/test-repo"
    respx.get(
        f"https://raw.githubusercontent.com/{repo}/main/README.md"
    ).mock(return_value=httpx.Response(200, text="Email: leaked@gmail.com"))

    results = await check_leaks(token="", repos=[repo])
    assert len(results) == 1
    row = results[0]
    assert row["check"].endswith("README")
    assert row["status"] == "FAIL"
    assert "leaked@gmail.com" in row["detail"]


@pytest.mark.asyncio
@respx.mock
async def test_check_leaks_pass_when_clean():
    repo = "perditioinc/test-repo"
    respx.get(
        f"https://raw.githubusercontent.com/{repo}/main/README.md"
    ).mock(return_value=httpx.Response(200, text="Contact ops@perditio.com"))

    results = await check_leaks(token="", repos=[repo])
    assert len(results) == 1
    assert results[0]["status"] == "PASS"


@pytest.mark.asyncio
@respx.mock
async def test_check_leaks_falls_back_to_master():
    repo = "perditioinc/test-repo"
    respx.get(
        f"https://raw.githubusercontent.com/{repo}/main/README.md"
    ).mock(return_value=httpx.Response(404))
    respx.get(
        f"https://raw.githubusercontent.com/{repo}/master/README.md"
    ).mock(return_value=httpx.Response(200, text="All clean."))

    results = await check_leaks(token="", repos=[repo])
    assert results[0]["status"] == "PASS"


@pytest.mark.asyncio
@respx.mock
async def test_check_leaks_warns_when_readme_missing():
    repo = "perditioinc/no-readme"
    respx.get(
        f"https://raw.githubusercontent.com/{repo}/main/README.md"
    ).mock(return_value=httpx.Response(404))
    respx.get(
        f"https://raw.githubusercontent.com/{repo}/master/README.md"
    ).mock(return_value=httpx.Response(404))

    results = await check_leaks(token="", repos=[repo])
    assert results[0]["status"] == "WARN"
