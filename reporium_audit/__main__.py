"""CLI entry point: python -m reporium_audit run"""

from __future__ import annotations

import asyncio
import logging
import os
import sys

from dotenv import load_dotenv

from reporium_audit.checks.api import check_api
from reporium_audit.checks.reporium_db import check_reporium_db
from reporium_audit.checks.workflows import check_workflows
from reporium_audit.reporter import generate_report

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def run_audit() -> str:
    """Run all audit checks and return the report."""
    api_url = os.getenv("REPORIUM_API_URL", "")
    gh_token = os.getenv("GH_TOKEN", "")

    if not api_url:
        logger.error("REPORIUM_API_URL is required")
        sys.exit(1)
    if not gh_token:
        logger.error("GH_TOKEN is required")
        sys.exit(1)

    logger.info("Running Reporium platform audit...")

    results = []
    api_results, db_results, wf_results = await asyncio.gather(
        check_api(api_url),
        check_reporium_db(gh_token),
        check_workflows(gh_token),
    )
    results.extend(api_results)
    results.extend(db_results)
    results.extend(wf_results)

    report = generate_report(results)

    with open("AUDIT_REPORT.md", "w", encoding="utf-8") as f:
        f.write(report)

    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    logger.info("Audit complete: %d passed, %d failed", passed, failed)

    return report


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "run":
        asyncio.run(run_audit())
    else:
        print("Usage: python -m reporium_audit run")


if __name__ == "__main__":
    main()
