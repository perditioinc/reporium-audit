"""Check knowledge graph edge count regressions via direct DB query."""

from __future__ import annotations

import os
from datetime import datetime, timezone

try:  # psycopg2 is an optional dep — if not installed, check self-skips.
    import psycopg2  # type: ignore
except ImportError:  # pragma: no cover - exercised by env rather than code
    psycopg2 = None  # type: ignore

GRAPH_STALE_HOURS = 25


async def check_knowledge_graph(db_url: str) -> list[dict]:
    """Check knowledge graph edge counts for regressions.

    Connects directly to the database (no HTTP) and queries the
    v_edge_count_by_run view to detect:
    - DEPENDS_ON count of 0 in the most recent run (FAIL)
    - Any edge_type dropping >20% vs the previous run (WARN / FAIL)

    Args:
        db_url: PostgreSQL connection string.

    Returns:
        List of check result dicts with check/status/detail keys.
    """
    results = []

    if not db_url:
        results.append({
            "check": "knowledge graph edge counts",
            "status": "SKIP",
            "detail": "DATABASE_URL not set",
        })
        return results

    if psycopg2 is None:
        results.append({
            "check": "knowledge graph edge counts",
            "status": "SKIP",
            "detail": "psycopg2 not installed",
        })
        return results

    try:
        conn = psycopg2.connect(db_url)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT run_id, edge_type, edge_count, started_at
                    FROM v_edge_count_by_run
                    ORDER BY started_at DESC
                    LIMIT 20
                    """
                )
                rows = cur.fetchall()
        finally:
            conn.close()
    except Exception as e:
        results.append({
            "check": "knowledge graph edge counts",
            "status": "FAIL",
            "detail": f"DB error: {str(e)[:120]}",
        })
        return results

    if not rows:
        results.append({
            "check": "knowledge graph edge counts",
            "status": "FAIL",
            "detail": "v_edge_count_by_run returned no rows",
        })
        return results

    # Group rows by run_id, preserving insertion order (rows already DESC by started_at)
    runs: dict[str, dict[str, int]] = {}
    run_order: list[str] = []
    for run_id, edge_type, edge_count, _started_at in rows:
        if run_id not in runs:
            runs[run_id] = {}
            run_order.append(run_id)
        runs[run_id][edge_type] = edge_count

    latest_run_id = run_order[0]
    latest = runs[latest_run_id]

    # --- Check 0: Latest run is fresh (< GRAPH_STALE_HOURS old) ---
    # ``rows`` is DESC by ``started_at``, so the first row's timestamp is
    # the freshest we have.
    latest_started_at = rows[0][3]
    if isinstance(latest_started_at, datetime):
        if latest_started_at.tzinfo is None:
            latest_started_at = latest_started_at.replace(tzinfo=timezone.utc)
        hours_ago = (datetime.now(timezone.utc) - latest_started_at).total_seconds() / 3600
        fresh = hours_ago < GRAPH_STALE_HOURS
        results.append({
            "check": "knowledge graph build freshness",
            "status": "PASS" if fresh else "FAIL",
            "detail": f"Latest run started {hours_ago:.1f}h ago (threshold {GRAPH_STALE_HOURS}h)",
        })
    else:
        results.append({
            "check": "knowledge graph build freshness",
            "status": "WARN",
            "detail": f"started_at not a datetime: {type(latest_started_at).__name__}",
        })

    # --- Check 1: DEPENDS_ON > 0 in most recent run ---
    depends_on_count = latest.get("DEPENDS_ON", 0)
    results.append({
        "check": "knowledge graph DEPENDS_ON > 0",
        "status": "PASS" if depends_on_count > 0 else "FAIL",
        "detail": f"DEPENDS_ON={depends_on_count} in run {latest_run_id}",
    })

    # --- Check 2: Regression vs previous run ---
    if len(run_order) < 2:
        results.append({
            "check": "knowledge graph edge count regression",
            "status": "PASS",
            "detail": "Only one run available — no regression baseline to compare",
        })
        return results

    prev_run_id = run_order[1]
    prev = runs[prev_run_id]

    all_types = set(latest.keys()) | set(prev.keys())
    regressions_warn: list[str] = []
    regressions_fail: list[str] = []

    for edge_type in sorted(all_types):
        current_count = latest.get(edge_type, 0)
        previous_count = prev.get(edge_type, 0)

        if previous_count == 0:
            # No baseline — skip drop check for this type
            continue

        drop_pct = (previous_count - current_count) / previous_count

        if drop_pct > 0.50:
            regressions_fail.append(
                f"{edge_type}: {previous_count} → {current_count} ({drop_pct:.0%} drop)"
            )
        elif drop_pct > 0.20:
            regressions_warn.append(
                f"{edge_type}: {previous_count} → {current_count} ({drop_pct:.0%} drop)"
            )

    if regressions_fail:
        results.append({
            "check": "knowledge graph edge count regression",
            "status": "FAIL",
            "detail": "; ".join(regressions_fail),
        })
    elif regressions_warn:
        results.append({
            "check": "knowledge graph edge count regression",
            "status": "WARN",
            "detail": "; ".join(regressions_warn),
        })
    else:
        all_type_summaries = [
            f"{et}={latest.get(et, 0)}" for et in sorted(all_types)
        ]
        results.append({
            "check": "knowledge graph edge count regression",
            "status": "PASS",
            "detail": f"No significant drops vs run {prev_run_id}. Counts: {', '.join(all_type_summaries)}",
        })

    return results
