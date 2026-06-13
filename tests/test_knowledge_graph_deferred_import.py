"""Tests pinning the lazy ``psycopg2`` import in the knowledge-graph check.

History (issue #13): ``psycopg2`` is intentionally NOT a declared dependency
of reporium-audit -- the runner's only hard deps are ``httpx`` and
``python-dotenv``. ``psycopg2`` is needed *only* when ``DATABASE_URL`` is set,
so the import lives inside ``check_knowledge_graph`` rather than at module top
level. These tests prove that contract two ways:

  1. The module imports, and the no-DB SKIP path runs, with ``psycopg2``
     completely unavailable -- a top-level ``import psycopg2`` would make
     even importing the module explode on a stock audit runner.
  2. When ``DATABASE_URL`` *is* set but ``psycopg2`` is missing, the check
     degrades to a clean FAIL row (not an uncaught ImportError).

To make the tests deterministic regardless of whether ``psycopg2`` happens
to be installed in the test venv, we force its absence via a context manager
that blocks the import (``sys.modules[name] = None`` makes ``import name``
raise ImportError, mirroring a runner that never installed the dep).
"""

from __future__ import annotations

import builtins
import contextlib
import importlib
import sys

import pytest


@contextlib.contextmanager
def _psycopg2_unavailable():
    """Force ``import psycopg2`` (and submodules) to raise ImportError.

    Restores the original import state on exit so the absence does not leak
    into other tests in the session.
    """
    blocked_prefix = "psycopg2"
    saved = {
        name: mod
        for name, mod in list(sys.modules.items())
        if name == blocked_prefix or name.startswith(blocked_prefix + ".")
    }
    for name in saved:
        del sys.modules[name]
    # A None entry in sys.modules makes `import psycopg2` raise ImportError.
    sys.modules[blocked_prefix] = None  # type: ignore[assignment]

    real_import = builtins.__import__

    def _guarded_import(name, *args, **kwargs):
        if name == blocked_prefix or name.startswith(blocked_prefix + "."):
            raise ImportError(f"No module named '{name}'")
        return real_import(name, *args, **kwargs)

    builtins.__import__ = _guarded_import
    try:
        yield
    finally:
        builtins.__import__ = real_import
        sys.modules.pop(blocked_prefix, None)
        sys.modules.update(saved)


def test_module_imports_without_psycopg2():
    """Importing the check module must not require ``psycopg2``.

    A regression to a top-level ``import psycopg2`` would raise here, on a
    fresh import of the module while psycopg2 is unavailable.
    """
    with _psycopg2_unavailable():
        sys.modules.pop("reporium_audit.checks.knowledge_graph", None)
        mod = importlib.import_module("reporium_audit.checks.knowledge_graph")
        assert hasattr(mod, "check_knowledge_graph")


@pytest.mark.asyncio
async def test_skip_path_never_touches_psycopg2():
    """The empty-DATABASE_URL SKIP path must run with psycopg2 absent.

    This is the audit-CI default (no DB credentials). It must SKIP, not
    FAIL, and must not depend on psycopg2 being importable.
    """
    with _psycopg2_unavailable():
        sys.modules.pop("reporium_audit.checks.knowledge_graph", None)
        mod = importlib.import_module("reporium_audit.checks.knowledge_graph")
        results = await mod.check_knowledge_graph("")

    assert len(results) == 1
    assert results[0]["status"] == "SKIP"
    assert "DATABASE_URL" in results[0]["detail"]


@pytest.mark.asyncio
async def test_configured_db_without_psycopg2_fails_cleanly():
    """DATABASE_URL set but psycopg2 missing -> a clean FAIL row, not a crash.

    The lazy import is wrapped in try/except ImportError so a runner that
    sets DATABASE_URL but forgot to install psycopg2 gets an actionable
    audit row rather than an uncaught traceback that aborts the whole run.
    """
    with _psycopg2_unavailable():
        sys.modules.pop("reporium_audit.checks.knowledge_graph", None)
        mod = importlib.import_module("reporium_audit.checks.knowledge_graph")
        results = await mod.check_knowledge_graph(
            "postgresql://user:pw@localhost:5432/db"
        )

    assert len(results) == 1
    row = results[0]
    assert row["status"] == "FAIL"
    assert "psycopg2" in row["detail"]


def teardown_module(module):
    """Re-import the module under normal conditions so later test files in
    the same session get the unguarded version back in sys.modules."""
    sys.modules.pop("reporium_audit.checks.knowledge_graph", None)
    importlib.import_module("reporium_audit.checks.knowledge_graph")
