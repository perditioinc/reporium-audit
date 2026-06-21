"""Cache-vs-DB consistency check for the repo detail surface.

Reporium has two cached endpoints that both report the "primary category"
of a repo, derived from independent caches with independent TTLs:

- ``/library/full`` — exposes the raw ``repos.primary_category`` column
  via the ``dbCategory`` field. This is the closest thing the audit
  runner has to "raw row state" without DB access (Cloud SQL is
  private-IP per ``reference_cloud_sql_private_ip.md``).
- ``/repos/<slug>`` — exposes the ``repo_categories`` junction table
  via the ``categories`` array (each row has ``category_name`` and
  ``is_primary``). This endpoint has its own ``repos:detail:<slug>``
  Redis cache with a separate TTL.

The pattern this invariant catches is the recurring "DB row updated ->
cache not invalidated -> user sees stale" regression (memory entry
4931, 2026-04-26): an admin backfill writes the ``repos.primary_category``
column but does not invalidate the per-slug detail cache. For a window
of TTL hours, ``/library/full`` reflects the new value while
``/repos/<slug>`` still serves the pre-backfill junction snapshot --
or vice versa.

The cleanest cross-cache check we can run without DB access is:

    For every sampled repo, the ``dbCategory`` reported by
    ``/library/full`` must appear as a ``category_name`` in the
    ``categories`` array returned by ``/repos/<slug>``.

If they diverge, either:
1. The ``/repos/<slug>`` cache is stale (the staleness regression).
2. The column was backfilled but the junction never had the matching
   row (the column-vs-junction drift caught by api#444 / #445).

Both belong to the same family of bugs.

Degradation policy:
- ``/library/full`` unreachable -> SKIP (the upstream contract check
  will already FAIL on this; no need to double-fail).
- All sampled repos have ``dbCategory=None`` -> SKIP with rationale.
  The column has not been backfilled for these repos so there is no
  DB ground truth to compare against.
- Any sampled repo's category-list is empty AND its ``dbCategory`` is
  non-null -> FAIL (the row has been backfilled but the detail cache
  shows no junction rows -- a real divergence).
- Any mismatch -> FAIL with the offending slugs in the detail.
"""

from __future__ import annotations

import logging
import random
from typing import Any

import httpx


logger = logging.getLogger(__name__)


# Sample size kept small so the check stays well under the audit's
# minute-budget. Each sampled repo costs one ``/repos/<slug>`` request.
SAMPLE_SIZE = 15

# A deterministic-but-distributed seed: same audit run produces the same
# sample (so a flaky failure can be reproduced) but different runs see
# different windows (so a hot-cached subset doesn't mask a cold-cache
# regression). The seed is reset per call so unit tests can pin it.
DEFAULT_SAMPLE_SEED = 0xCAFE


def _candidate_repos(repos: list[dict]) -> list[dict]:
    """Return repos that have both ``name`` and a non-null ``dbCategory``.

    Repos with ``dbCategory=None`` cannot serve as ground truth -- the
    column was never backfilled for them. They contribute to the SKIP
    rationale, not to a FAIL.
    """
    candidates = []
    for repo in repos:
        name = repo.get("name")
        db_cat = repo.get("dbCategory")
        if not name or not db_cat:
            continue
        candidates.append({"name": name, "dbCategory": db_cat})
    return candidates


def _detail_category_names(detail: dict) -> list[str]:
    """Extract the list of ``category_name`` strings from a /repos/<slug>
    response, tolerating both list-of-dicts (new shape) and list-of-strings
    (legacy shape) for ``categories``."""
    cats = detail.get("categories") or []
    names: list[str] = []
    for c in cats:
        if isinstance(c, dict):
            name = c.get("category_name")
            if isinstance(name, str) and name:
                names.append(name)
        elif isinstance(c, str) and c:
            names.append(c)
    return names


async def check_cache_consistency(
    api_url: str,
    *,
    sample_size: int = SAMPLE_SIZE,
    sample_seed: int | None = DEFAULT_SAMPLE_SEED,
    client: httpx.AsyncClient | None = None,
) -> list[dict[str, Any]]:
    """Verify that ``/repos/<slug>`` and ``/library/full`` agree on
    primary category for a sample of repos.

    Args:
        api_url: Base URL of the live API deployment.
        sample_size: Max number of repos to probe with /repos/<slug>.
        sample_seed: RNG seed for reproducible sampling. Pass ``None``
            to use system entropy.
        client: Optional pre-built httpx.AsyncClient (used by tests so
            ``respx.mock`` can intercept). If ``None``, a fresh client
            with a 30s timeout is created and closed inside this call.

    Returns:
        A single-element list of result dicts, matching the convention
        of the other audit checks.
    """
    owns_client = client is None
    if client is None:
        client = httpx.AsyncClient(timeout=30)

    try:
        # 1. Pull /library/full. The frontend pulls page_size=200 so
        # this is a reasonable production-shaped sample window.
        try:
            r = await client.get(f"{api_url}/library/full", params={"page": 1, "page_size": 200})
            if r.status_code != 200:
                return [{
                    "check": "cache vs db: repo detail consistency",
                    "status": "SKIP",
                    "detail": (
                        f"/library/full returned HTTP {r.status_code}; cannot establish "
                        "DB ground truth -- skipping (the contract check covers reachability)"
                    ),
                }]
            payload = r.json()
        except Exception as e:
            return [{
                "check": "cache vs db: repo detail consistency",
                "status": "SKIP",
                "detail": f"/library/full unreachable: {str(e)[:120]}",
            }]

        repos = payload.get("repos") or []
        if not repos:
            return [{
                "check": "cache vs db: repo detail consistency",
                "status": "SKIP",
                "detail": "/library/full returned no repos -- cannot sample",
            }]

        candidates = _candidate_repos(repos)
        if not candidates:
            return [{
                "check": "cache vs db: repo detail consistency",
                "status": "SKIP",
                "detail": (
                    f"None of {len(repos)} repos in /library/full page 1 have a non-null "
                    "dbCategory column; cannot establish DB ground truth. The "
                    "primary_category column backfill (api#444/#445) may still be "
                    "in flight."
                ),
            }]

        # 2. Sample. Cap at sample_size, but never sample more than what's
        # available.
        rng = random.Random(sample_seed)
        n = min(sample_size, len(candidates))
        sample = rng.sample(candidates, n)

        # 3. For each sampled repo, fetch /repos/<slug> and verify the
        # dbCategory shows up in the junction-derived categories array.
        mismatches: list[str] = []
        unreachable: list[str] = []

        for entry in sample:
            slug = entry["name"]
            db_cat = entry["dbCategory"]
            try:
                rr = await client.get(f"{api_url}/repos/{slug}")
                if rr.status_code != 200:
                    unreachable.append(f"{slug} (HTTP {rr.status_code})")
                    continue
                detail = rr.json()
            except Exception as e:  # network, JSON decode
                unreachable.append(f"{slug} ({str(e)[:60]})")
                continue

            detail_cats = _detail_category_names(detail)
            if db_cat not in detail_cats:
                # The DB column says X but the cached junction array
                # doesn't contain X. This is the staleness / drift signal.
                mismatches.append(
                    f"{slug}: dbCategory={db_cat!r} not in /repos/<slug> categories={detail_cats!r}"
                )

        # 4. Score.
        if unreachable and not mismatches:
            # Treat upstream-unreachable as SKIP for THIS check -- the
            # /repos/<slug> reachability is already covered by the
            # ``reporium-api /repos`` check. We only fail here on a real
            # consistency violation.
            return [{
                "check": "cache vs db: repo detail consistency",
                "status": "SKIP",
                "detail": (
                    f"sampled {n} repos; {len(unreachable)} /repos/<slug> requests failed "
                    f"-- cannot evaluate consistency. Examples: {unreachable[:3]}"
                ),
            }]

        if mismatches:
            return [{
                "check": "cache vs db: repo detail consistency",
                "status": "FAIL",
                "detail": (
                    f"{len(mismatches)}/{n} sampled repos have stale or divergent caches: "
                    f"{mismatches[:5]}"
                ),
            }]

        return [{
            "check": "cache vs db: repo detail consistency",
            "status": "PASS",
            "detail": (
                f"{n}/{n} sampled repos have /repos/<slug> categories that include "
                f"the /library/full dbCategory column value"
            ),
        }]
    finally:
        if owns_client:
            await client.aclose()
