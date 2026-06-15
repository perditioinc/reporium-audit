"""Tests that the KG check is wired into the runner and degrades safely.

Before 2026-04-24, ``knowledge_graph.py`` existed but was never imported
by ``__main__``. This test pins the import so the regression can't
recur silently.

The remaining tests pin the issue-#13 degradation policy: the runner
gathers checks with ``asyncio.gather``, so a raw ``ImportError`` or
crash inside any check aborts the entire audit. Both no-``DATABASE_URL``
and missing-``psycopg2`` paths must return a result row, not raise.
"""

from __future__ import annotations

import sys

import pytest

from reporium_audit import __main__ as runner
from reporium_audit.checks.knowledge_graph import check_knowledge_graph


def test_knowledge_graph_is_imported_by_runner():
    # If the name is not on the module, the check is dead code again.
    assert hasattr(runner, "check_knowledge_graph")


@pytest.mark.asyncio
async def test_knowledge_graph_skips_when_db_url_missing():
    results = await check_knowledge_graph("")
    assert len(results) == 1
    assert results[0]["status"] == "SKIP"
    assert "DATABASE_URL" in results[0]["detail"]


@pytest.mark.asyncio
async def test_knowledge_graph_does_not_crash_when_psycopg2_missing(monkeypatch):
    """Missing ``psycopg2`` must surface as a result row, not a raised
    ``ImportError``. Otherwise the runner's ``asyncio.gather`` would
    propagate the error and abort the full audit (issue #13)."""
    monkeypatch.setitem(sys.modules, "psycopg2", None)

    results = await check_knowledge_graph("postgresql://unused-host/db")

    assert isinstance(results, list)
    assert len(results) == 1
    row = results[0]
    assert row["status"] in {"FAIL", "SKIP"}
    assert "psycopg2" in row["detail"]


@pytest.mark.asyncio
async def test_knowledge_graph_skip_path_does_not_import_psycopg2(monkeypatch):
    """The empty-``DATABASE_URL`` SKIP path must not require ``psycopg2``.

    The audit's declared deps are httpx + python-dotenv only; importing
    ``psycopg2`` at module top would crash CI envs that have no DB
    access, regardless of whether ``DATABASE_URL`` was set."""
    monkeypatch.setitem(sys.modules, "psycopg2", None)

    results = await check_knowledge_graph("")

    assert len(results) == 1
    assert results[0]["status"] == "SKIP"
    assert "DATABASE_URL" in results[0]["detail"]
