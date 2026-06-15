"""Tests for audit reporter.

The reporter is the operator-facing surface of the audit -- these
tests pin the behaviour that keeps the 3am triage loop tight:
remediation hints on known failures, a Next Actions section so the
operator doesn't have to scroll, and familiarity-sorted Failures so
genuinely novel failures stand out at the bottom.
"""

from reporium_audit.reporter import (
    _actions_url_for,
    _hint_for,
    _sort_failures,
    generate_report,
)


# --- Original smoke tests -------------------------------------------------

def test_generate_report_all_passing():
    results = [
        {"check": "reporium-api /health", "status": "PASS", "detail": "ok"},
        {"check": "reporium-api /repos", "status": "PASS", "detail": "826 repos"},
    ]
    report = generate_report(results)
    assert "2/2 checks passed" in report
    assert "Failures" not in report
    # No failures/warns -> no Next Actions block either.
    assert "Next Actions" not in report


def test_generate_report_with_failures():
    results = [
        {"check": "reporium-api /health", "status": "PASS", "detail": "ok"},
        {"check": "forksync CI", "status": "FAIL", "detail": "Nightly Fork Sync: failure"},
    ]
    report = generate_report(results)
    assert "1 failures" in report
    assert "forksync CI" in report


def test_generate_report_with_warnings():
    results = [
        {"check": "cache", "status": "WARN", "detail": "Redis disabled"},
    ]
    report = generate_report(results)
    assert "Warnings" in report


# --- Remediation hint table ----------------------------------------------

def test_hint_for_known_api_check():
    hint = _hint_for("reporium-api /health")
    assert hint
    assert "Cloud Run" in hint


def test_hint_for_private_repo_leak_is_highest_priority():
    # This failure is the single most sensitive -- the hint must
    # explicitly point at the forksync visibility audit first.
    hint = _hint_for("contract: no private/fork repos exposed")
    assert "forksync" in hint.lower()


def test_hint_for_depends_on_regression_references_kan119():
    # The canonical prior incident is KAN-119; hint should jog memory.
    hint = _hint_for("knowledge graph DEPENDS_ON > 0")
    assert "KAN-119" in hint or "kan-119" in hint.lower()


def test_hint_for_schedule_vs_generic_ci_specificity_beats_genericity():
    # A scheduled-workflow failure ("<repo> schedule: <wf>") must hit
    # the schedule-specific hint, not the generic " ci" hint.
    schedule_hint = _hint_for("reporium-api schedule: Data Quality Check")
    generic_hint = _hint_for("reporium-api CI")
    assert "workflow_dispatch" in schedule_hint
    assert schedule_hint != generic_hint


def test_hint_for_unknown_check_is_empty():
    # Silence beats a bogus generic hint.
    assert _hint_for("some brand new check we never registered") == ""


# --- Actions-URL inference ------------------------------------------------

def test_actions_url_for_repo_ci_check():
    assert (
        _actions_url_for("reporium-db CI")
        == "https://github.com/perditioinc/reporium-db/actions"
    )


def test_actions_url_for_scheduled_workflow():
    assert (
        _actions_url_for("reporium-ingestion schedule: Nightly Graph Build")
        == "https://github.com/perditioinc/reporium-ingestion/actions"
    )


def test_actions_url_for_leak_check_points_at_repo_not_leaks_word():
    # The "leaks: " prefix is not a repo; we must resolve to the repo
    # slug that follows, not mint https://.../perditioinc/leaks/actions.
    url = _actions_url_for("leaks: perditioinc/reporium-api README")
    assert url == "https://github.com/perditioinc/reporium-api/actions"


def test_actions_url_for_non_repo_check_is_empty():
    # Checks that aren't about a specific repo (drift, cloud run tags,
    # contract) must return "" -- a wrong link would be worse than no
    # link because it sends the operator to the wrong page.
    assert _actions_url_for("drift: api vs db repo count") == ""
    assert _actions_url_for("cloud run candidate tags") == ""
    assert _actions_url_for("contract: no null required fields") == ""


# --- Sort order ----------------------------------------------------------

def test_sort_failures_puts_known_first_and_preserves_order():
    failures = [
        {"check": "mystery unknown failure", "status": "FAIL", "detail": "?"},
        {"check": "reporium-db CI", "status": "FAIL", "detail": "bad"},
        {"check": "another unknown", "status": "FAIL", "detail": "?"},
        {"check": "reporium-api /health", "status": "FAIL", "detail": "bad"},
    ]
    ordered = _sort_failures(failures)
    names = [f["check"] for f in ordered]
    assert names == [
        "reporium-db CI",
        "reporium-api /health",
        "mystery unknown failure",
        "another unknown",
    ]


# --- End-to-end report shape ---------------------------------------------

def test_generate_report_next_actions_absent_when_all_green():
    results = [{"check": "reporium-api /health", "status": "PASS", "detail": "ok"}]
    report = generate_report(results)
    assert "Next Actions" not in report


def test_generate_report_next_actions_includes_hint_and_link():
    results = [
        {"check": "reporium-db CI", "status": "FAIL", "detail": "Nightly Sync: failure"},
    ]
    report = generate_report(results)
    # Next Actions comes before Failures section.
    na_idx = report.index("## Next Actions")
    fail_idx = report.index("## Failures")
    assert na_idx < fail_idx
    # Hint and link both present on the Next Actions line.
    next_actions_section = report[na_idx:fail_idx]
    assert "Actions tab" in next_actions_section  # hint phrase
    assert "https://github.com/perditioinc/reporium-db/actions" in next_actions_section


def test_generate_report_hint_column_populated_for_failures_and_warns():
    results = [
        {"check": "reporium-api /health", "status": "PASS", "detail": "ok"},
        {"check": "reporium-db CI", "status": "FAIL", "detail": "Nightly Sync: failure"},
        {"check": "reporium-metrics CI", "status": "WARN", "detail": "No runs"},
    ]
    report = generate_report(results)
    # Table header gains a Hint column.
    assert "| Check | Status | Detail | Hint |" in report
    # The PASS row gets an empty hint cell; the FAIL row gets a hint.
    pass_row = next(
        line for line in report.splitlines()
        if "reporium-api /health" in line and "PASS" in line
    )
    fail_row = next(
        line for line in report.splitlines()
        if "reporium-db CI" in line and "FAIL" in line
    )
    assert pass_row.rstrip().endswith("|")  # trailing empty Hint cell
    assert "Actions tab" in fail_row


def test_generate_report_unknown_failure_rendered_without_hint_or_link():
    results = [
        {"check": "mystery novel failure", "status": "FAIL", "detail": "something"},
    ]
    report = generate_report(results)
    assert "## Next Actions" in report
    na_section = report.split("## Next Actions", 1)[1].split("##", 1)[0]
    # The failure appears, but with no hint phrase and no actions link.
    assert "mystery novel failure" in na_section
    assert "https://github.com/" not in na_section
