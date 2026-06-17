#!/usr/bin/env python3
"""Generate fixtures for the GitHub OSS substitutes (api.github.com + raw).

The audit (dev branch) hardcodes ``https://api.github.com`` and
``https://raw.githubusercontent.com`` (they are NOT env-pointed). The local
substrate redirects those hostnames to a local nginx via Docker network aliases
plus a self-signed cert trusted through ``SSL_CERT_FILE`` -- so the audit's real
HTTPS code path runs unmodified. This script bakes the static responses nginx
serves at the matching paths.

api.github.com surfaces (reporium_audit/checks/workflows.py):
  /repos/<owner>/<repo>/actions/runs  -> {"workflow_runs": [{"conclusion": "success", ...}]}

raw.githubusercontent.com surfaces (reporium_audit/checks/reporium_db.py):
  /perditioinc/reporium-db/main/data/index.json -> {"meta": {"total", "last_updated"}}

index.json freshness (last_updated < 25h) is stamped at container start by the
entrypoint, not here, so it is always fresh on ``make up``.
"""
from __future__ import annotations

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
API_ROOT = os.path.normpath(os.path.join(HERE, "..", "mock-api"))
RAW_ROOT = os.path.normpath(os.path.join(HERE, "..", "mock-raw"))

# ACTIVE_SUITE_REPOS from reporium_audit/checks/workflows.py (dev branch).
WORKFLOW_REPOS = [
    "reporium", "reporium-api", "reporium-audit", "reporium-db",
    "reporium-dataset", "reporium-events", "reporium-ingestion",
    "reporium-metrics", "reporium-roadmap", "reporium-scoring",
    "reporium-security", "reporium-system-design",
]


def runs_payload(repo: str) -> dict:
    """A workflow_runs page whose latest run is a green CI run, so the
    'latest run conclusion == success' gate PASSes for this repo."""
    return {
        "total_count": 1,
        "workflow_runs": [
            {
                "name": "CI",
                "conclusion": "success",
                "status": "completed",
                "run_started_at": "2026-06-07T08:00:00Z",
                "created_at": "2026-06-07T08:00:00Z",
                "head_branch": "main",
                "display_title": "CI on main",
            }
        ],
    }


def main() -> None:
    # --- api.github.com/repos/perditioinc/<repo>/actions/runs ---
    for repo in WORKFLOW_REPOS:
        d = os.path.join(API_ROOT, "repos", "perditioinc", repo, "actions")
        os.makedirs(d, exist_ok=True)
        # nginx serves this file for the ".../actions/runs" path (query ignored).
        with open(os.path.join(d, "runs"), "w", encoding="utf-8") as f:
            json.dump(runs_payload(repo), f, indent=2)

    # reporium-db index.json directory (content stamped by entrypoint for freshness)
    os.makedirs(
        os.path.join(RAW_ROOT, "perditioinc", "reporium-db", "main", "data"),
        exist_ok=True,
    )

    print(f"Generated GitHub API fixtures -> {API_ROOT}")
    print(f"Generated raw fixtures        -> {RAW_ROOT}")


if __name__ == "__main__":
    main()
