"""Generate AUDIT_REPORT.md from check results.

The nightly issue is usually opened on a phone at an unpleasant hour.
The goal of this module is therefore not just to *list* what failed,
but to answer the operator's two immediate questions before they have
to scroll:

1. "What do I look at first?"  -> the **Next Actions** section.
2. "Where in GitHub / the console do I click?" -> the per-failure
   remediation hint (and, when inferable, a direct link to the failing
   repo's Actions tab).

The check contract (``{"check", "status", "detail"}``) is unchanged --
hints are derived from the check name alone, so no check has to emit
extra metadata for a hint to appear next to its failure.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

STATUS_ICON = {
    "PASS": "\u2713",
    "FAIL": "\u2717",
    "WARN": "\u26a0",
    "SKIP": "\u2014",
}


# Remediation hints. Each entry is ``(substring_matcher, hint_text)``.
# Matching is case-insensitive substring on the check name; order
# matters -- more specific matchers must come before generic ones
# (e.g. "knowledge graph DEPENDS_ON" before "knowledge graph").
#
# Keep hints short and *directional* -- they should tell the operator
# which tab to open or which workflow to re-dispatch, not re-explain
# the failure (the detail body already does that).
REMEDIATION_HINTS: list[tuple[str, str]] = [
    # reporium-api
    (
        "reporium-api /health",
        "Check Cloud Run revision health; inspect the most recent deploy run in reporium-api Actions.",
    ),
    (
        "reporium-api /repos",
        "Likely DB connectivity -- check Cloud SQL pool stats and the last migration in reporium-api logs.",
    ),
    (
        "reporium-api /search",
        "API reachable but search empty -- check embeddings availability and the search index endpoint.",
    ),
    # Contract
    (
        "contract: no private/fork repos exposed",
        "Private/fork repo leaking via /library/full -- run the forksync visibility audit before any other triage.",
    ),
    (
        "contract: no null required fields",
        "Enrichment pipeline gap -- check reporium-ingestion's last nightly run for skipped rows.",
    ),
    (
        "contract: no null enriched fields",
        "Enrichment arrays came back null -- inspect the last enrichment job; arrays should degrade to [] not null.",
    ),
    (
        "contract: /library/full",
        "Contract endpoint itself is unreachable -- start with reporium-api /health.",
    ),
    # reporium-db
    (
        "reporium-db index.json fresh",
        "Nightly Sync workflow in reporium-db stalled; re-dispatch it or open the last run log.",
    ),
    (
        "reporium-db repo count",
        "Ingestion dropped rows -- compare against forksync output and the last reporium-ingestion run.",
    ),
    (
        "reporium-db index.json",
        "Raw index.json fetch failed -- check raw.githubusercontent.com availability and the last reporium-db commit.",
    ),
    # Knowledge graph (specific before generic)
    (
        "knowledge graph build freshness",
        "Nightly Graph Build in reporium-ingestion stalled; re-dispatch and watch for the next run.",
    ),
    (
        "knowledge graph DEPENDS_ON",
        "DEPENDS_ON edges collapsed -- classic KAN-119-style regression; compare the latest v_edge_count_by_run row to previous.",
    ),
    (
        "knowledge graph edge count regression",
        "Compare the latest run in v_edge_count_by_run to the previous; likely enrichment or ingestion change.",
    ),
    (
        "knowledge graph",
        "Graph check failed -- open reporium-ingestion Nightly Graph Build and inspect the latest run log.",
    ),
    # Cloud Run / deploy
    (
        "cloud run candidate tag",
        "Stale traffic tag on reporium-api; apply the deploy.yml cleanup or run `gcloud run services update-traffic --remove-tags`.",
    ),
    # Drift
    (
        "drift:",
        "Cross-source count delta -- re-run nightly ingestion; confirm /repos, /library/full, and index.json converge.",
    ),
    # Leaks
    (
        "leaks:",
        "README hit forbidden pattern -- if a real secret, rotate it first; then open a PR to redact.",
    ),
    # Scheduled workflow -- match before generic CI.
    (
        "schedule:",
        "Scheduled run failed even if latest run is green -- a manual workflow_dispatch may be masking a red cron. Re-check event=schedule runs.",
    ),
    # Generic CI failure -- ``<repo> CI``.
    (
        " ci",
        "Open the repo's Actions tab; the latest run's conclusion is not success -- drill into the failing job.",
    ),
]


# Pattern that extracts a repo slug from the check names the runner
# emits today. Matches "reporium-api CI", "reporium-db schedule:
# Nightly Sync", "perditioinc/repo-intelligence workflows", and
# "leaks: perditioinc/reporium-audit README".
_REPO_NAME_RE = re.compile(
    r"(?:leaks:\s*)?(?:perditioinc/)?"
    r"(?P<repo>[a-z][a-z0-9-]+)"
    # ``schedule:`` ends in a non-word char so a trailing ``\b`` would
    # not match -- anchor each alternative on its own boundary.
    r"\s+(?:CI\b|schedule:|workflows\b|README\b)",
    re.IGNORECASE,
)

# Slugs the regex might catch that aren't really repos.
_NON_REPO_WORDS = {"leaks", "contract", "drift", "cloud", "knowledge"}


def _hint_for(check_name: str) -> str:
    """Return the remediation hint for a check, or ``""`` if none registered.

    Silence beats a bogus generic hint -- an unknown check means we
    haven't yet encoded what to do about it, and the operator should
    treat it as a genuinely novel failure.
    """
    lowered = check_name.lower()
    for matcher, hint in REMEDIATION_HINTS:
        if matcher.lower() in lowered:
            return hint
    return ""


def _actions_url_for(check_name: str) -> str:
    """Best-effort GitHub Actions deep-link for checks that name a repo.

    Returns ``""`` when no repo slug can be extracted. Resolution is
    deliberately heuristic -- a wrong link would be worse than no link,
    so the regex only fires on check-name shapes the runner actually
    emits today.
    """
    m = _REPO_NAME_RE.search(check_name)
    if not m:
        return ""
    repo = m.group("repo").lower()
    if repo in _NON_REPO_WORDS:
        return ""
    return f"https://github.com/perditioinc/{repo}/actions"


def _sort_failures(failures: list[dict]) -> list[dict]:
    """Sort so hint-carrying (well-understood) failures come first.

    Counter-intuitive but deliberate: well-understood failures have a
    clear next click, so operators can clear them fast. The *unknown*
    failures then stand out at the bottom as the residual thing that
    needs fresh thought, rather than being buried in the middle of a
    list where they look routine.

    Within each group the original order is preserved so the report
    diffs cleanly night to night.
    """
    known = [f for f in failures if _hint_for(f["check"])]
    unknown = [f for f in failures if not _hint_for(f["check"])]
    return known + unknown


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

    failures = [r for r in results if r["status"] == "FAIL"]
    warns = [r for r in results if r["status"] == "WARN"]

    # Next Actions -- the first thing an on-call operator reads.
    # FAILs in familiarity order, then WARNs, each with a hint and
    # (when inferable) a direct Actions link.
    if failures or warns:
        lines.append("## Next Actions")
        lines.append("")
        ordered = _sort_failures(failures) + warns
        for r in ordered:
            icon = STATUS_ICON.get(r["status"], "?")
            hint = _hint_for(r["check"])
            url = _actions_url_for(r["check"])
            link = f" \u2192 [Actions]({url})" if url else ""
            hint_str = f" {hint}" if hint else ""
            lines.append(f"- {icon} **{r['check']}**:{hint_str}{link}")
        lines.append("")

    # Failures -- kept so downstream consumers that grep this section
    # keep working. Sorted familiarity-first here too.
    if failures:
        lines.append("## Failures")
        lines.append("")
        for r in _sort_failures(failures):
            lines.append(f"- **{r['check']}**: {r['detail']}")
        lines.append("")

    if warns:
        lines.append("## Warnings")
        lines.append("")
        for r in warns:
            lines.append(f"- **{r['check']}**: {r['detail']}")
        lines.append("")

    # Full results table -- gains a Hint column. Empty cell when no
    # hint is registered; PASS/SKIP rows get an empty cell too since
    # there is no action to take.
    lines.append("## Full Results")
    lines.append("")
    lines.append("| Check | Status | Detail | Hint |")
    lines.append("|-------|--------|--------|------|")
    for r in results:
        icon = STATUS_ICON.get(r["status"], "?")
        hint = _hint_for(r["check"]) if r["status"] in {"FAIL", "WARN"} else ""
        lines.append(
            f"| {r['check']} | {icon} {r['status']} | {r['detail']} | {hint} |"
        )

    lines.append("")
    lines.append(f"*Generated at {datetime.now(timezone.utc).isoformat()}*")
    return "\n".join(lines)
