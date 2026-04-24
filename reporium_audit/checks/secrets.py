"""Scan public repo READMEs for leaked-secret regression signals.

Complements ``checks.leaks`` (which looks for non-allowlisted email
addresses). This check scans the same README surfaces for *structured*
credential patterns: a leaked GitHub token, GCP key, AWS access key, or
private key is strictly worse than the personal-email regression that
inspired ``leaks`` — and today none of the audit checks would notice.

Design notes
------------
- Patterns are anchored (word boundary + full expected length) so a
  prose mention of ``ghp_``, ``AKIA``, or ``AIza...`` does **not** fire
  a false positive.
- No new secrets are required to run this — it only needs
  ``https://raw.githubusercontent.com`` access. ``GH_TOKEN`` is honored
  only to dodge the 60/hr anonymous rate limit.
- Any hit is a ``FAIL``. We never ``WARN`` on a credential-shaped
  substring: if it matched the structural pattern, the right answer
  is "treat it as leaked until proved otherwise".
- Detail output **redacts** the match down to a short prefix so the
  audit report itself never rebroadcasts the secret.

Residual blind spots (documented):
- Non-README files (CODEOWNERS, docs/, ADRs).
- Commit history — a secret added and later removed from HEAD is not
  caught here.
- Provider-specific fingerprinting (e.g. verifying a
  ``AKIA...``-shaped substring is actually an AWS account). Upstream
  scanners like ``gitleaks`` do this; we explicitly stay pattern-only
  to keep the audit zero-credential.
"""

from __future__ import annotations

import os
import re

import httpx

# High-confidence leaked-secret patterns.
SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("github-token", re.compile(r"\b(?:ghp|ghs|gho|ghu|ghr)_[A-Za-z0-9]{36,}\b")),
    ("github-fine-grained-pat", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{22,}\b")),
    ("google-api-key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("aws-access-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("slack-token", re.compile(r"\bxox[abpr]-[0-9A-Za-z-]{10,}\b")),
    ("private-key-pem", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
]

# Kept in sync with ``checks.leaks.DEFAULT_REPOS`` intentionally — both
# checks target the same README surface, and a repo joining that
# surface should be flipped on for both at once. Duplicating the list
# (rather than importing) keeps this module independent of the leaks
# lane's in-flight changes.
DEFAULT_REPOS = [
    "perditioinc/reporium-api",
    "perditioinc/reporium-audit",
    "perditioinc/reporium-db",
    "perditioinc/portfolio",
    "perditioinc/reporium-ingestion",
    "perditioinc/reporium-events",
    "perditioinc/reporium-metrics",
]


def _allowlist() -> list[str]:
    raw = os.getenv("AUDIT_SECRET_ALLOWLIST", "").strip()
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def scan_for_secret_patterns(text: str) -> list[tuple[str, str]]:
    """Return ``(pattern_name, matched_substring)`` pairs for every hit.

    Substrings listed in ``AUDIT_SECRET_ALLOWLIST`` (comma-separated)
    suppress matches that contain any allowlist entry — useful when a
    doc legitimately references a redacted prefix like
    ``ghp_REDACTED...``.
    """
    allowlist = _allowlist()
    hits: list[tuple[str, str]] = []
    for name, pattern in SECRET_PATTERNS:
        for match in pattern.finditer(text):
            value = match.group(0)
            if any(item in value for item in allowlist):
                continue
            hits.append((name, value))
    return hits


def _redact(value: str, keep: int = 4) -> str:
    """Return a short prefix followed by an ellipsis.

    The report must never re-broadcast a full credential. Four chars
    is enough for an operator to tell ``ghp_`` from ``AKIA`` and to
    grep for the specific hit in the source README.
    """
    return f"{value[:keep]}…"


async def check_readme_secrets(
    token: str = "",
    repos: list[str] | None = None,
) -> list[dict]:
    """Fetch each repo's README and FAIL on any structured secret hit."""
    repos = repos or DEFAULT_REPOS
    results: list[dict] = []

    headers: dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    async with httpx.AsyncClient(timeout=15, headers=headers) as client:
        for repo in repos:
            check_name = f"secrets: {repo} README"
            content: str | None = None
            fetch_error: str | None = None
            for branch in ("main", "master"):
                url = f"https://raw.githubusercontent.com/{repo}/{branch}/README.md"
                try:
                    r = await client.get(url)
                except Exception as e:
                    fetch_error = f"fetch error: {str(e)[:80]}"
                    break
                if r.status_code == 200:
                    content = r.text
                    break
                if r.status_code == 404:
                    continue
                fetch_error = f"HTTP {r.status_code} on {branch}"
                break

            if fetch_error:
                results.append({
                    "check": check_name,
                    "status": "WARN",
                    "detail": fetch_error,
                })
                continue

            if content is None:
                results.append({
                    "check": check_name,
                    "status": "WARN",
                    "detail": "README.md not found on main or master",
                })
                continue

            hits = scan_for_secret_patterns(content)
            if hits:
                redacted = [f"{name}:{_redact(value)}" for name, value in hits[:3]]
                results.append({
                    "check": check_name,
                    "status": "FAIL",
                    "detail": f"{len(hits)} secret pattern hit(s): {redacted}",
                })
            else:
                results.append({
                    "check": check_name,
                    "status": "PASS",
                    "detail": "No known secret patterns",
                })

    return results
