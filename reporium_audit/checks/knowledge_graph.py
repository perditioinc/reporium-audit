"""Check knowledge graph edge count regressions via direct DB query."""

from __future__ import annotations

import os

import psycopg2


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
            "status": "FAIL",
            "detail": "DATABASE_URL not set",
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
