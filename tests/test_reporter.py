"""Tests for audit reporter."""

from reporium_audit.reporter import generate_report


def test_generate_report_all_passing():
    results = [
        {"check": "api /health", "status": "PASS", "detail": "ok"},
        {"check": "api /repos", "status": "PASS", "detail": "826 repos"},
    ]
    report = generate_report(results)
    assert "2/2 checks passed" in report
    assert "Failures" not in report


def test_generate_report_with_failures():
    results = [
        {"check": "api /health", "status": "PASS", "detail": "ok"},
        {"check": "forksync stale", "status": "FAIL", "detail": "2 days old"},
    ]
    report = generate_report(results)
    assert "1 failures" in report
    assert "forksync stale" in report


def test_generate_report_with_warnings():
    results = [
        {"check": "cache", "status": "WARN", "detail": "Redis disabled"},
    ]
    report = generate_report(results)
    assert "Warnings" in report


def test_generate_report_with_skips():
    results = [
        {"check": "api /health", "status": "PASS", "detail": "ok"},
        {"check": "kg edges", "status": "SKIP", "detail": "DATABASE_URL not set"},
    ]
    report = generate_report(results)
    assert "Skipped" in report
    assert "DATABASE_URL not set" in report
    # A SKIP must not be counted as a failure.
    assert "failures" not in report.lower()
