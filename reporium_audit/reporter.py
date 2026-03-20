"""Generate AUDIT_REPORT.md from check results."""

from __future__ import annotations

from datetime import datetime, timezone


def generate_report(results: list[dict]) -> str:
    """Generate markdown audit report from check results."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    warnings = sum(1 for r in results if r["status"] == "WARN")
    total = len(results)

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
    lines.append(" | ".join(status_parts))
    lines.append("")

    # Failures
    failures = [r for r in results if r["status"] == "FAIL"]
    if failures:
        lines.append("## Failures")
        lines.append("")
        for r in failures:
            lines.append(f"- **{r['check']}**: {r['detail']}")
        lines.append("")

    # Warnings
    warns = [r for r in results if r["status"] == "WARN"]
    if warns:
        lines.append("## Warnings")
        lines.append("")
        for r in warns:
            lines.append(f"- **{r['check']}**: {r['detail']}")
        lines.append("")

    # Full results table
    lines.append("## Full Results")
    lines.append("")
    lines.append("| Check | Status | Detail |")
    lines.append("|-------|--------|--------|")
    for r in results:
        icon = {"PASS": "\u2713", "FAIL": "\u2717", "WARN": "\u26a0"}.get(r["status"], "?")
        lines.append(f"| {r['check']} | {icon} {r['status']} | {r['detail']} |")

    lines.append("")
    lines.append(f"*Generated at {datetime.now(timezone.utc).isoformat()}*")
    return "\n".join(lines)
