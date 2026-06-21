"""Knowledge graph health checks: edge-count regressions and build freshness.

These checks connect directly to the database (``DATABASE_URL``) and
query ``v_edge_count_by_run`` -- the view that tracks edge counts per
nightly run of the graph-build job.

History: this module existed on ``main`` long before it was wired into
``__main__.py``. That silent-dead-code state is exactly what let
KAN-119's DEPENDS_ON regression ship unnoticed. ``tests/test_knowledge
_graph_wiring.py`` now pins the import so the regression cannot recur.

Degradation policy:
- No ``DATABASE_URL`` -> ``SKIP`` (with a note in the detail). Audit
  CI does not always have DB credentials, and we want the missing-gap
  to be visible in the report without reddening it.
- DB unreachable -> ``FAIL`` (a configured URL that doesn't work is a
  real failure, not a "not applicable").
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


STALE_RUN_THRESHOLD = timedelta(hours=25)


async def check_knowledge_graph(db_url: str) -> list[dict]:
    """Check knowledge graph health: edge counts and build freshness.

    Args:
        db_url: PostgreSQL connection string. Empty string -> SKIP.

    Returns:
        List of check result dicts with ``check``/``status``/``detail`` keys.
    """
    results: list[dict] = []

    if not db_url:
        results.append({
            "check": "knowledge graph edge counts",
            "status": "SKIP",
            "detail": "DATABASE_URL not set -- audit runner has no DB credentials",
        })
        return results

    # psycopg2 is imported lazily so the SKIP path above doesn't require the
    # dep. The audit's declared deps are httpx + python-dotenv only; psycopg2
    # is only needed when DATABASE_URL is set (issue #13).
    try:
        import psycopg2
    except ImportError as e:
        results.append({
            "check": "knowledge graph edge counts",
            "status": "FAIL",
            "detail": f"psycopg2 not installed: {e}",
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

    runs: dict[str, dict[str, int]] = {}
    run_order: list[str] = []
    run_started: dict[str, datetime] = {}
    for run_id, edge_type, edge_count, started_at in rows:
        if run_id not in runs:
            runs[run_id] = {}
            run_order.append(run_id)
            run_started[run_id] = started_at
        runs[run_id][edge_type] = edge_count

    latest_run_id = run_order[0]
    latest = runs[latest_run_id]

    # --- Check: build freshness ---
    latest_started = run_started.get(latest_run_id)
    if latest_started is None:
        results.append({
            "check": "knowledge graph build freshness",
            "status": "WARN",
            "detail": "latest run has no started_at timestamp",
        })
    else:
        if latest_started.tzinfo is None:
            latest_started = latest_started.replace(tzinfo=timezone.utc)
        age = datetime.now(timezone.utc) - latest_started
        if age > STALE_RUN_THRESHOLD:
            results.append({
                "check": "knowledge graph build freshness",
                "status": "FAIL",
                "detail": (
                    f"latest run {latest_run_id} is {age.total_seconds() / 3600:.1f}h "
                    f"old (> {STALE_RUN_THRESHOLD.total_seconds() / 3600:.0f}h)"
                ),
            })
        else:
            results.append({
                "check": "knowledge graph build freshness",
                "status": "PASS",
                "detail": (
                    f"latest run {latest_run_id} is {age.total_seconds() / 3600:.1f}h old"
                ),
            })

    # --- Check: DEPENDS_ON > 0 in most recent run ---
    depends_on_count = latest.get("DEPENDS_ON", 0)
    results.append({
        "check": "knowledge graph DEPENDS_ON > 0",
        "status": "PASS" if depends_on_count > 0 else "FAIL",
        "detail": f"DEPENDS_ON={depends_on_count} in run {latest_run_id}",
    })

    # --- Check: regression vs previous run ---
    if len(run_order) < 2:
        results.append({
            "check": "knowledge graph edge count regression",
            "status": "PASS",
            "detail": "Only one run available -- no regression baseline to compare",
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
            continue

        drop_pct = (previous_count - current_count) / previous_count

        if drop_pct > 0.50:
            regressions_fail.append(
                f"{edge_type}: {previous_count} -> {current_count} ({drop_pct:.0%} drop)"
            )
        elif drop_pct > 0.20:
            regressions_warn.append(
                f"{edge_type}: {previous_count} -> {current_count} ({drop_pct:.0%} drop)"
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
            "detail": (
                f"No significant drops vs run {prev_run_id}. "
                f"Counts: {', '.join(all_type_summaries)}"
            ),
        })

    return results
