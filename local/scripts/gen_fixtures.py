#!/usr/bin/env python3
"""Generate local fixture JSON for the reporium-api OSS substitute (nginx).

The real audit code (reporium_audit/checks/*) on the `dev` integration branch is
the source of truth for the exact response shapes. This script bakes fixtures
that satisfy every gate so a healthy local run produces an all-PASS report. To
rehearse a failure mode, edit a fixture (e.g. flip a repo's isPrivate to true)
and re-run the smoke.

Surfaces produced (served by nginx as static files):
  static/library_full.json   -> GET /library/full   (contract check)
  static/repos_list.json     -> GET /repos          (api check)
  static/search.json         -> GET /search         (api check)

Contract invariants enforced by reporium_audit/checks/contract.py that the
fixtures must satisfy:
  - isPrivate must be falsy on every repo (no private exposed)
  - REQUIRED_FIELDS all non-null/non-empty
  - ENRICHED_FIELDS all non-null (lists are lists, dicts are dicts)
  - fullName == "owner/name" (exactly one slash)
  - fullName values unique; name values unique (collisions only WARN)
  - url.rstrip("/").endswith(fullName)   <-- url must END with owner/name
"""
from __future__ import annotations

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.normpath(os.path.join(HERE, "..", "static"))

REPO_COUNT = 120  # > 100 so reporium-db count gate passes; also > 0 everywhere
OWNER = "perditioinc"


def make_repo(i: int) -> dict:
    name = f"sample-repo-{i:03d}"
    full_name = f"{OWNER}/{name}"
    return {
        "name": name,
        "fullName": full_name,
        "description": f"Local fixture repo #{i} for the OSS audit substrate.",
        # url MUST end with fullName (contract: repo URLs match fullName).
        "url": f"https://example.local/{full_name}",
        "stars": 10 + i,
        "forks": i % 7,
        # Privacy contract: not private.
        "isPrivate": False,
        # Enriched fields: lists are lists, dicts are dicts, none null.
        "readmeSummary": f"Summary for {name}.",
        "primaryCategory": "AI Tooling",
        "allCategories": ["AI Tooling"],
        "enrichedTags": ["local", "fixture"],
        "builders": [],
        "pmSkills": [],
        "industries": [],
        "aiDevSkills": [],
        "programmingLanguages": ["Python"],
        "commitStats": {"total": 42},
        "languageBreakdown": {"Python": 100},
        "languagePercentages": {"Python": 100.0},
    }


def main() -> None:
    repos = [make_repo(i) for i in range(REPO_COUNT)]
    os.makedirs(STATIC, exist_ok=True)

    # /library/full -> {"repos": [...]}
    with open(os.path.join(STATIC, "library_full.json"), "w", encoding="utf-8") as f:
        json.dump({"repos": repos}, f, indent=2)

    # /repos?limit=1 -> {"total": N, "repos": [...]}
    with open(os.path.join(STATIC, "repos_list.json"), "w", encoding="utf-8") as f:
        json.dump({"total": len(repos), "repos": repos[:1]}, f, indent=2)

    # /search?q=python -> JSON array (len > 0)
    with open(os.path.join(STATIC, "search.json"), "w", encoding="utf-8") as f:
        json.dump(repos[:20], f, indent=2)

    print(f"Generated {len(repos)} repos -> {STATIC}")


if __name__ == "__main__":
    main()
