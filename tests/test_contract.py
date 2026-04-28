"""Tests for /library/full data-contract checks.

Pins:
  - the 2026-04-26 fix that stopped conflating ``isFork`` with ``isPrivate``
    (forks are the product surface, not a privacy violation)
  - the 2026-04-28 fix that stopped silently passing when the API omitted
    the ``isPrivate`` field entirely (the hippo-harvest-assignment leak
    surfaced for ~22 hours because the contract check returned PASS even
    though no privacy signal was being emitted at all)
"""

from __future__ import annotations

import httpx
import pytest
import respx

from reporium_audit.checks.contract import (
    check_contract,
    check_static_artifact,
)


API_URL = "https://api.example.test"
LIBRARY_FULL_URL = f"{API_URL}/library/full"
STATIC_URL = "https://reporium-test.example/data/library.json"


def _repo(
    name: str,
    *,
    is_fork: bool = False,
    privacy: str | None = "public",
) -> dict:
    """Build a contract-shaped repo fixture.

    ``privacy`` ∈ {"public", "private", None, "snake_public", "snake_private"}:
      - "public" / "private"        → camelCase isPrivate field
      - "snake_public" / "snake_private" → snake_case is_private field
      - None                        → field absent entirely (the leak shape)
    """
    repo: dict = {
        "name": name,
        "fullName": f"perditioinc/{name}",
        "description": "x",
        "url": f"https://github.com/perditioinc/{name}",
        "stars": 1,
        "forks": 0,
        "isFork": is_fork,
        # enriched fields populated to keep null-checks PASS
        "readmeSummary": "x",
        "primaryCategory": "ai",
        "allCategories": [],
        "enrichedTags": [],
        "builders": [],
        "pmSkills": [],
        "industries": [],
        "aiDevSkills": [],
        "programmingLanguages": [],
        "commitStats": {},
        "languageBreakdown": {},
        "languagePercentages": {},
    }
    if privacy == "public":
        repo["isPrivate"] = False
    elif privacy == "private":
        repo["isPrivate"] = True
    elif privacy == "snake_public":
        repo["is_private"] = False
    elif privacy == "snake_private":
        repo["is_private"] = True
    elif privacy is None:
        pass  # field absent — the bug surface this lane fixes
    else:
        raise ValueError(f"unknown privacy value: {privacy!r}")
    return repo


def _row_named(results: list[dict], substring: str) -> dict:
    """Return the first row whose ``check`` field contains the substring."""
    matches = [r for r in results if substring in r["check"]]
    assert len(matches) >= 1, f"no row with {substring!r} in {results}"
    return matches[0]


# ---------------------------------------------------------------------------
# Fork / private separation (2026-04-26 regression guard — kept intact)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_forks_alone_do_not_trigger_privacy_failure():
    """Regression: forks are the product surface, not a privacy violation."""
    repos = [_repo(f"fork-{i}", is_fork=True) for i in range(3)]
    respx.get(LIBRARY_FULL_URL).mock(
        return_value=httpx.Response(200, json={"repos": repos})
    )

    results = await check_contract(API_URL)

    leak_row = _row_named(results, "no private repos exposed")
    assert leak_row["status"] == "PASS"
    assert "fork" not in leak_row["check"]


@pytest.mark.asyncio
@respx.mock
async def test_clean_public_originals_pass():
    repos = [_repo("original-1"), _repo("fork-1", is_fork=True)]
    respx.get(LIBRARY_FULL_URL).mock(
        return_value=httpx.Response(200, json={"repos": repos})
    )

    results = await check_contract(API_URL)

    leak_row = _row_named(results, "no private repos exposed")
    assert leak_row["status"] == "PASS"


# ---------------------------------------------------------------------------
# Private-exposure detection — both naming conventions, both rows
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_camelcase_is_private_true_triggers_failure():
    repos = [_repo("public-fork", is_fork=True), _repo("leaked", privacy="private")]
    respx.get(LIBRARY_FULL_URL).mock(
        return_value=httpx.Response(200, json={"repos": repos})
    )

    results = await check_contract(API_URL)

    leak_row = _row_named(results, "no private repos exposed")
    assert leak_row["status"] == "FAIL"
    assert "leaked" in leak_row["detail"]


@pytest.mark.asyncio
@respx.mock
async def test_snake_case_is_private_true_triggers_failure():
    """API may emit ``is_private`` (snake_case). The check must catch both."""
    repos = [_repo("ok", privacy="public"), _repo("leaked", privacy="snake_private")]
    respx.get(LIBRARY_FULL_URL).mock(
        return_value=httpx.Response(200, json={"repos": repos})
    )

    results = await check_contract(API_URL)

    leak_row = _row_named(results, "no private repos exposed")
    assert leak_row["status"] == "FAIL"
    assert "leaked" in leak_row["detail"]


@pytest.mark.asyncio
@respx.mock
async def test_snake_case_is_private_false_passes():
    repos = [_repo("a", privacy="snake_public"), _repo("b", privacy="snake_public")]
    respx.get(LIBRARY_FULL_URL).mock(
        return_value=httpx.Response(200, json={"repos": repos})
    )

    results = await check_contract(API_URL)

    leak_row = _row_named(results, "no private repos exposed")
    field_row = _row_named(results, "privacy field present")
    assert leak_row["status"] == "PASS"
    assert field_row["status"] == "PASS"


@pytest.mark.asyncio
@respx.mock
async def test_mixed_field_naming_recognized():
    """Some repos use isPrivate, others use is_private — both must be honored."""
    repos = [
        _repo("camel-public", privacy="public"),
        _repo("snake-public", privacy="snake_public"),
        _repo("snake-private", privacy="snake_private"),
    ]
    respx.get(LIBRARY_FULL_URL).mock(
        return_value=httpx.Response(200, json={"repos": repos})
    )

    results = await check_contract(API_URL)

    leak_row = _row_named(results, "no private repos exposed")
    assert leak_row["status"] == "FAIL"
    assert "snake-private" in leak_row["detail"]


# ---------------------------------------------------------------------------
# Missing-field detection — the 2026-04-27 hippo silent-pass bug
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_missing_privacy_field_fails_audit():
    """If NO repo emits a privacy field, the contract check must FAIL.

    This is the bug exercise: prior to 2026-04-28 the check used
    ``repo.get("isPrivate")`` which returns None for missing fields, which
    is falsy, so every repo silently passed — the
    perditioinc/hippo-harvest-assignment leak went undetected for ~22h.
    """
    repos = [_repo(f"r{i}", privacy=None) for i in range(3)]
    respx.get(LIBRARY_FULL_URL).mock(
        return_value=httpx.Response(200, json={"repos": repos})
    )

    results = await check_contract(API_URL)

    field_row = _row_named(results, "privacy field present")
    assert field_row["status"] == "FAIL", (
        f"missing privacy field must FAIL the audit (got {field_row}). "
        "This was the silent-pass bug from 2026-04-27."
    )
    assert "3" in field_row["detail"]


@pytest.mark.asyncio
@respx.mock
async def test_partial_missing_privacy_field_fails_audit():
    """Even one repo without a privacy field should fail the field-present check."""
    repos = [
        _repo("ok-1", privacy="public"),
        _repo("missing", privacy=None),
        _repo("ok-2", privacy="public"),
    ]
    respx.get(LIBRARY_FULL_URL).mock(
        return_value=httpx.Response(200, json={"repos": repos})
    )

    results = await check_contract(API_URL)

    field_row = _row_named(results, "privacy field present")
    assert field_row["status"] == "FAIL"
    assert "missing" in field_row["detail"]


@pytest.mark.asyncio
@respx.mock
async def test_missing_field_does_not_pretend_repo_is_private():
    """Missing field is a SEPARATE failure mode from "private repo exposed".

    Past temptation: treat missing as private and roll into one row. Don't —
    operators need to distinguish "API broken / awaiting deploy" from "leak
    in production". Two rows = two distinct signals.
    """
    repos = [_repo("missing", privacy=None)]
    respx.get(LIBRARY_FULL_URL).mock(
        return_value=httpx.Response(200, json={"repos": repos})
    )

    results = await check_contract(API_URL)

    field_row = _row_named(results, "privacy field present")
    leak_row = _row_named(results, "no private repos exposed")
    assert field_row["status"] == "FAIL"
    # The leak row should NOT also fail — there's no positive private signal.
    assert leak_row["status"] == "PASS"


# ---------------------------------------------------------------------------
# Static-artifact check — same gates against reporium.com/data/library.json
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_static_artifact_catches_private_repo():
    """The frontend artifact at reporium.com/data/library.json is a separate
    surface — even if the API is clean, a stale artifact can leak. The
    static-artifact check must run the same privacy gates."""
    repos = [_repo("ok", privacy="public"), _repo("leaked-artifact", privacy="private")]
    respx.get(STATIC_URL).mock(
        return_value=httpx.Response(200, json={"repos": repos})
    )

    results = await check_static_artifact(STATIC_URL)

    leak_row = _row_named(results, "static artifact: no private repos exposed")
    assert leak_row["status"] == "FAIL"
    assert "leaked-artifact" in leak_row["detail"]


@pytest.mark.asyncio
@respx.mock
async def test_static_artifact_missing_field_fails():
    """The 2026-04-27 incident: live artifact had no privacy field on any
    of 1862 repos. The static-artifact check must hard-fail this state."""
    repos = [_repo(f"r{i}", privacy=None) for i in range(5)]
    respx.get(STATIC_URL).mock(
        return_value=httpx.Response(200, json={"repos": repos})
    )

    results = await check_static_artifact(STATIC_URL)

    field_row = _row_named(results, "static artifact: privacy field present")
    assert field_row["status"] == "FAIL"


@pytest.mark.asyncio
@respx.mock
async def test_static_artifact_clean_passes():
    repos = [_repo("a", privacy="public"), _repo("b", privacy="public")]
    respx.get(STATIC_URL).mock(
        return_value=httpx.Response(200, json={"repos": repos})
    )

    results = await check_static_artifact(STATIC_URL)

    leak_row = _row_named(results, "static artifact: no private repos exposed")
    field_row = _row_named(results, "static artifact: privacy field present")
    assert leak_row["status"] == "PASS"
    assert field_row["status"] == "PASS"


@pytest.mark.asyncio
@respx.mock
async def test_static_artifact_unreachable_fails():
    respx.get(STATIC_URL).mock(return_value=httpx.Response(503))

    results = await check_static_artifact(STATIC_URL)

    reach_row = _row_named(results, "static artifact: reachable")
    assert reach_row["status"] == "FAIL"
    assert "503" in reach_row["detail"]
