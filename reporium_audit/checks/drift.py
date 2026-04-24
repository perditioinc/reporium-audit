"""Cross-source suite drift detection.

The audit already proves each surface is individually "alive" (the API
responds, ``index.json`` is fresh, the graph build ran recently). None
of those surfaces is cross-checked against the others, so a whole class
of silent failures is invisible today:

- Ingestion drops half the repos on its next run. ``/repos`` still
  returns a non-zero total; ``index.json`` is still fresh; every
  existing check stays green.
- A migration truncates an enrichment table. ``/library/full`` still
  returns repos but the count diverges from ``reporium-db``.
- The API points at a stale Cloud SQL replica. ``/repos`` lags
  ``index.json`` by thousands of rows without either side failing.

This check treats the three populated-independently repo counts as a
small consensus vote and flags significant disagreement.

Thresholds are intentionally loose — near-midnight windows can briefly
have a one- or two-repo delta while nightly jobs stagger. Callers can
tune via ``AUDIT_DRIFT_WARN_PCT`` and ``AUDIT_DRIFT_FAIL_PCT``.
"""

from __future__ import annotations

import os

import httpx

DB_INDEX_URL = (
    "https://raw.githubusercontent.com/perditioinc/reporium-db/main/data/index.json"
)

DEFAULT_WARN_PCT = 0.01  # > 1% delta → WARN
DEFAULT_FAIL_PCT = 0.05  # > 5% delta → FAIL
MIN_ABSOLUTE_DELTA = 2   # < 2 repos of drift is noise, never a finding


def _threshold(env_var: str, default: float) -> float:
    raw = os.getenv(env_var)
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


async def _fetch_api_repos_total(client: httpx.AsyncClient, api_url: str) -> int | None:
    try:
        r = await client.get(f"{api_url}/repos?limit=1")
        if r.status_code != 200:
            return None
        return int(r.json().get("total", 0))
    except Exception:
        return None


async def _fetch_api_library_total(client: httpx.AsyncClient, api_url: str) -> int | None:
    try:
        r = await client.get(f"{api_url}/library/full")
        if r.status_code != 200:
            return None
        data = r.json()
        repos = data.get("repos")
        if not isinstance(repos, list):
            return None
        return len(repos)
    except Exception:
        return None


async def _fetch_db_index_total(
    client: httpx.AsyncClient, token: str
) -> int | None:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        r = await client.get(DB_INDEX_URL, headers=headers)
        if r.status_code != 200:
            return None
        return int(r.json().get("meta", {}).get("total", 0))
    except Exception:
        return None


def _classify_drift(
    counts: dict[str, int | None],
    warn_pct: float,
    fail_pct: float,
) -> tuple[str, str]:
    """Return ``(status, detail)`` for a map of source -> count.

    ``None`` values represent unreachable sources and are reported
    separately — they do not on their own turn the check red, because
    each source has its own dedicated check elsewhere.
    """
    present = {src: c for src, c in counts.items() if c is not None}
    missing = [src for src, c in counts.items() if c is None]

    if len(present) < 2:
        return (
            "WARN",
            f"Not enough reachable sources to compare drift (have {list(present)})",
        )

    lowest = min(present.values())
    highest = max(present.values())
    abs_delta = highest - lowest

    if highest == 0:
        return ("FAIL", "All reachable sources report 0 repos")

    pct = abs_delta / highest
    summary = ", ".join(f"{src}={cnt}" for src, cnt in sorted(present.items()))
    missing_note = f" (unreachable: {missing})" if missing else ""
    delta_note = f"max Δ={abs_delta} ({pct:.1%})"

    if abs_delta < MIN_ABSOLUTE_DELTA:
        return ("PASS", f"{summary}; {delta_note}{missing_note}")

    if pct > fail_pct:
        return ("FAIL", f"{summary}; {delta_note}{missing_note}")
    if pct > warn_pct:
        return ("WARN", f"{summary}; {delta_note}{missing_note}")

    return ("PASS", f"{summary}; {delta_note}{missing_note}")


async def check_suite_drift(api_url: str, token: str = "") -> list[dict]:
    """Reconcile reporium-api and reporium-db repo counts.

    Args:
        api_url: Base URL for reporium-api.
        token: GitHub token, used only to avoid the 60/hr anonymous
            rate limit when fetching the raw ``index.json``. Not
            required.
    """
    if not api_url:
        return [{
            "check": "drift: api vs db repo count",
            "status": "SKIP",
            "detail": "REPORIUM_API_URL not set",
        }]

    warn_pct = _threshold("AUDIT_DRIFT_WARN_PCT", DEFAULT_WARN_PCT)
    fail_pct = _threshold("AUDIT_DRIFT_FAIL_PCT", DEFAULT_FAIL_PCT)

    async with httpx.AsyncClient(timeout=30) as client:
        api_repos = await _fetch_api_repos_total(client, api_url)
        api_library = await _fetch_api_library_total(client, api_url)
        db_index = await _fetch_db_index_total(client, token)

    counts = {
        "api:/repos": api_repos,
        "api:/library/full": api_library,
        "db:index.json": db_index,
    }

    status, detail = _classify_drift(counts, warn_pct, fail_pct)
    return [{
        "check": "drift: api vs db repo count",
        "status": status,
        "detail": detail,
    }]
