"""Scan public repo READMEs for private-leak regression signals.

The 2026-04-16 incident ("personal email leaking into a public README")
was only caught by a human. This check fetches the raw README from a
curated set of public repos and flags any email address whose domain is
not in the allowlist.

Configuration
-------------
The allowlist of trusted email domains defaults to ``perditio.com`` and
``perditioinc.com``. Extra domains can be supplied via the
``AUDIT_ALLOWED_EMAIL_DOMAINS`` env var (comma-separated). GitHub's
noreply addresses (``users.noreply.github.com``) are always allowed
because they're a common and non-sensitive artefact of signed commits.

This check only needs a public HTTP fetch — no token required — but
will use ``GH_TOKEN`` if provided to avoid the 60/hr anonymous rate
limit.
"""

from __future__ import annotations

import os
import re

import httpx

EMAIL_RE = re.compile(r"\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\b", re.IGNORECASE)

DEFAULT_ALLOWED_DOMAINS = {
    "perditio.com",
    "perditioinc.com",
    "users.noreply.github.com",
    "noreply.github.com",
}

# High-confidence leaked-secret patterns. Anchored so we don't flag
# ``AKIA...`` written in prose; each pattern is matched at a word
# boundary with the full expected length / structure.
#
# Tested against the current `perditioinc/*` README corpus — all clean
# as of 2026-04-24. If a legitimate doc needs to reference a key format
# verbatim, add it to the allowlist via ``AUDIT_SECRET_ALLOWLIST``
# (comma-separated literal substrings).
SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("github-token", re.compile(r"\b(ghp|ghs|gho|ghu|ghr)_[A-Za-z0-9]{36,}\b")),
    ("github-fine-grained-pat", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{22,}\b")),
    ("google-api-key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("aws-access-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("slack-token", re.compile(r"\bxox[abpr]-[0-9A-Za-z-]{10,}\b")),
    (
        "private-key-pem",
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    ),
]

# Public repos whose READMEs must stay clean. Kept intentionally short —
# every addition is another HTTP fetch per audit run.
DEFAULT_REPOS = [
    "perditioinc/reporium-api",
    "perditioinc/reporium-audit",
    "perditioinc/reporium-db",
    "perditioinc/portfolio",
    "perditioinc/reporium-ingestion",
    "perditioinc/reporium-events",
    "perditioinc/reporium-metrics",
]


def _allowed_domains() -> set[str]:
    extra = os.getenv("AUDIT_ALLOWED_EMAIL_DOMAINS", "").strip()
    if not extra:
        return set(DEFAULT_ALLOWED_DOMAINS)
    extras = {d.strip().lower() for d in extra.split(",") if d.strip()}
    return DEFAULT_ALLOWED_DOMAINS | extras


def _scan_for_forbidden_emails(text: str, allowed: set[str]) -> list[str]:
    hits: list[str] = []
    for match in EMAIL_RE.findall(text):
        domain = match.split("@", 1)[1].lower()
        if domain in allowed:
            continue
        if any(domain.endswith("." + a) or domain == a for a in allowed):
            continue
        hits.append(match)
    return hits


def _secret_allowlist() -> list[str]:
    raw = os.getenv("AUDIT_SECRET_ALLOWLIST", "").strip()
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def _scan_for_secret_patterns(text: str) -> list[tuple[str, str]]:
    """Return ``(pattern_name, matched_substring)`` pairs for every hit.

    Secret allowlist entries (set via ``AUDIT_SECRET_ALLOWLIST``) are
    compared as literal substrings so docs can legitimately reference
    a redacted prefix like ``ghp_REDACTED`` without tripping the
    check.
    """
    allowlist = _secret_allowlist()
    hits: list[tuple[str, str]] = []
    for name, pattern in SECRET_PATTERNS:
        for match in pattern.finditer(text):
            value = match.group(0)
            if any(item in value for item in allowlist):
                continue
            hits.append((name, value))
    return hits


async def check_leaks(
    token: str = "",
    repos: list[str] | None = None,
) -> list[dict]:
    """Fetch each repo's README and report any non-allowlisted emails."""
    repos = repos or DEFAULT_REPOS
    allowed = _allowed_domains()
    results: list[dict] = []

    headers: dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    async with httpx.AsyncClient(timeout=15, headers=headers) as client:
        for repo in repos:
            check_name = f"leaks: {repo} README"
            found = False
            content: str | None = None
            for branch in ("main", "master"):
                url = f"https://raw.githubusercontent.com/{repo}/{branch}/README.md"
                try:
                    r = await client.get(url)
                except Exception as e:
                    results.append({
                        "check": check_name,
                        "status": "FAIL",
                        "detail": f"fetch error: {str(e)[:80]}",
                    })
                    found = True
                    break
                if r.status_code == 200:
                    content = r.text
                    found = True
                    break
                if r.status_code == 404:
                    continue
                results.append({
                    "check": check_name,
                    "status": "FAIL",
                    "detail": f"HTTP {r.status_code} on {branch}",
                })
                found = True
                break

            if not found:
                results.append({
                    "check": check_name,
                    "status": "WARN",
                    "detail": "README.md not found on main or master",
                })
                continue

            if content is None:
                continue

            hits = _scan_for_forbidden_emails(content, allowed)
            if hits:
                # Deduplicate while preserving order.
                seen: list[str] = []
                for h in hits:
                    if h not in seen:
                        seen.append(h)
                results.append({
                    "check": check_name,
                    "status": "FAIL",
                    "detail": f"{len(seen)} forbidden email(s): {seen[:3]}",
                })
            else:
                results.append({
                    "check": check_name,
                    "status": "PASS",
                    "detail": "No forbidden emails",
                })

            secret_hits = _scan_for_secret_patterns(content)
            secret_check_name = f"leaks: {repo} README secrets"
            if secret_hits:
                # Show pattern name + short prefix so the report is
                # readable without echoing the full credential.
                redacted = [
                    f"{name}:{value[:4]}…" for name, value in secret_hits[:3]
                ]
                results.append({
                    "check": secret_check_name,
                    "status": "FAIL",
                    "detail": f"{len(secret_hits)} secret pattern hit(s): {redacted}",
                })
            else:
                results.append({
                    "check": secret_check_name,
                    "status": "PASS",
                    "detail": "No known secret patterns",
                })

    return results
