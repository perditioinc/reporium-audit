"""Tests that the KG check is wired into the runner and degrades safely.

Before 2026-04-24, ``knowledge_graph.py`` existed but was never imported
by ``__main__``. This test pins the import so the regression can't
recur silently.
"""

from __future__ import annotations

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
