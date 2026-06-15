"""Generate AUDIT_REPORT.md from check results.

Layout is deliberately top-heavy: an operator reading the nightly issue
on their phone should be able to see *which area* is broken and *what
to look at first* without scrolling to a 30-row table. The area banner
and "Attention" section do that work; the existing Failures / Warnings
/ Skipped / Full Results sections are kept so downstream tooling
(nightly diffs, the GitHub Issue creator) doesn't need to change.
"""

from __future__ import annotations

from datetime import datetime, timezone

# Area inference is pure-function on the check name. Order matters —
# more specific prefixes must come before generic ones.
AREA_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("Schedule", ("schedule:",)),  # "<repo> schedule: ..."
    ("Security", ("leaks:",)),
    ("Contract", ("contract:",)),
    ("Drift", ("drift:",)),
    ("Graph", ("knowledge graph",)),
    ("Cloud Run", ("cloud run",)),
    ("DB", ("reporium-db",)),
    ("API", ("reporium-api",)),
]

# Stable order the banner and Attention section use, so the report is
# diff-friendly night to night.
AREA_ORDER = [area for area, _ in AREA_RULES] + ["CI", "Other"]


def _area_for(check_name: str) -> str:
    lowered = check_name.lower()
    for area, prefixes in AREA_RULES:
        if any(p in lowered for p in prefixes):
            return area
    # Fallback: any per-repo workflow check is CI.
    if "ci" in lowered.split() or lowered.endswith(" ci"):
        return "CI"
    return "Other"


def _area_status(results_in_area: list[dict]) -> str:
    """Area-level rollup: FAIL beats WARN beats PASS beats SKIP."""
    if not results_in_area:
        return "SKIP"
    statuses = {r["status"] for r in results_in_area}
    for ranked in ("FAIL", "WARN", "PASS", "SKIP"):
        if ranked in statuses:
            return ranked
    return "SKIP"


STATUS_ICON = {
    "PASS": "\u2713",
    "FAIL": "\u2717",
    "WARN": "\u26a0",
    "SKIP": "\u2014",
}


def generate_report(results: list[dict]) -> str:
    """Generate markdown audit report from check results."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    warnings = sum(1 for r in results if r["status"] == "WARN")
    skipped = sum(1 for r in results if r["status"] == "SKIP")
    total = len(results)

    # Group once; both the banner and the Attention section reuse this.
    by_area: dict[str, list[dict]] = {area: [] for area in AREA_ORDER}
    for r in results:
        by_area.setdefault(_area_for(r["check"]), []).append(r)

    lines = [
        f"# Reporium Audit Report \u2014 {now}",
        "",
        "## Summary",
        "",
    ]

    status_parts = []
    if passed:
        status_parts.append(f"\u2713 {passed}/{total} checks passed")
    if failed:
        status_parts.append(f"\u2717 {failed} failures")
    if warnings:
        status_parts.append(f"\u26a0 {warnings} warnings")
    if skipped:
        status_parts.append(f"\u2014 {skipped} skipped")
    lines.append(" | ".join(status_parts))
    lines.append("")

    # Area banner — skip empty areas entirely; no value in "Other ✓" when
    # no check mapped to Other.
    banner_parts: list[str] = []
    for area in AREA_ORDER:
        area_results = by_area.get(area, [])
        if not area_results:
            continue
        banner_parts.append(
            f"{area} {STATUS_ICON[_area_status(area_results)]}"
        )
    if banner_parts:
        lines.append("**Area status:** " + " | ".join(banner_parts))
        lines.append("")

    # Attention section — FAIL only, grouped by area. This is the
    # "what should I look at first" answer.
    if failed:
        lines.append("## Attention")
        lines.append("")
        for area in AREA_ORDER:
            area_fails = [
                r for r in by_area.get(area, []) if r["status"] == "FAIL"
            ]
            if not area_fails:
                continue
            lines.append(f"### {area}")
            lines.append("")
            for r in area_fails:
                lines.append(f"- **{r['check']}**: {r['detail']}")
            lines.append("")

    # Keep Failures / Warnings / Skipped blocks so existing consumers
    # (issue creator, nightly diff) don't drift.
    failures = [r for r in results if r["status"] == "FAIL"]
    if failures:
        lines.append("## Failures")
        lines.append("")
        for r in failures:
            lines.append(f"- **{r['check']}**: {r['detail']}")
        lines.append("")

    warns = [r for r in results if r["status"] == "WARN"]
    if warns:
        lines.append("## Warnings")
        lines.append("")
        for r in warns:
            lines.append(f"- **{r['check']}**: {r['detail']}")
        lines.append("")

    skips = [r for r in results if r["status"] == "SKIP"]
    if skips:
        lines.append("## Skipped")
        lines.append("")
        for r in skips:
            lines.append(f"- **{r['check']}**: {r['detail']}")
        lines.append("")

    # Full results table
    lines.append("## Full Results")
    lines.append("")
    lines.append("| Area | Check | Status | Detail |")
    lines.append("|------|-------|--------|--------|")
    for r in results:
        icon = STATUS_ICON.get(r["status"], "?")
        area = _area_for(r["check"])
        lines.append(
            f"| {area} | {r['check']} | {icon} {r['status']} | {r['detail']} |"
        )

    lines.append("")
    lines.append(f"*Generated at {datetime.now(timezone.utc).isoformat()}*")
    return "\n".join(lines)
