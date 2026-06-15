"""CLI entry point: python -m reporium_audit run"""

from __future__ import annotations

import asyncio
import logging
import os
import sys

from dotenv import load_dotenv

from reporium_audit.checks.api import check_api
from reporium_audit.checks.cloud_run_tags import check_cloud_run_tags
from reporium_audit.checks.contract import check_contract
from reporium_audit.checks.drift import check_suite_drift
from reporium_audit.checks.knowledge_graph import check_knowledge_graph
from reporium_audit.checks.leaks import check_leaks
from reporium_audit.checks.reporium_db import check_reporium_db
from reporium_audit.checks.workflows import check_scheduled_workflows, check_workflows
from reporium_audit.reporter import generate_report

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def _run_graph_check(db_url: str) -> list[dict]:
    """Wrap the sync KG check so it composes with asyncio.gather.

    ``check_knowledge_graph`` declares async but does blocking psycopg2
    work; isolate it here so future changes don't leak into the runner.
    """
    return await check_knowledge_graph(db_url)


async def run_audit() -> str:
    """Run all audit checks and return the report."""
    api_url = os.getenv("REPORIUM_API_URL", "")
    gh_token = os.getenv("GH_TOKEN", "")
    db_url = os.getenv("DATABASE_URL", "")

    if not api_url:
        logger.error("REPORIUM_API_URL is required")
        sys.exit(1)
    if not gh_token:
        logger.error("GH_TOKEN is required")
        sys.exit(1)

    logger.info("Running Reporium platform audit...")

    (
        api_results,
        contract_results,
        db_results,
        wf_results,
        scheduled_results,
        tag_results,
        leak_results,
        kg_results,
        drift_results,
    ) = await asyncio.gather(
        check_api(api_url),
        check_contract(api_url),
        check_reporium_db(gh_token),
        check_workflows(gh_token),
        check_scheduled_workflows(gh_token),
        check_cloud_run_tags(api_url, gh_token),
        check_leaks(gh_token),
        _run_graph_check(db_url),
        check_suite_drift(api_url, gh_token),
    )

    results: list[dict] = []
    results.extend(api_results)
    results.extend(contract_results)
    results.extend(db_results)
    results.extend(wf_results)
    results.extend(scheduled_results)
    results.extend(tag_results)
    results.extend(leak_results)
    results.extend(kg_results)
    results.extend(drift_results)

    report = generate_report(results)

    with open("AUDIT_REPORT.md", "w", encoding="utf-8") as f:
        f.write(report)

    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    skipped = sum(1 for r in results if r["status"] == "SKIP")
    logger.info(
        "Audit complete: %d passed, %d failed, %d skipped", passed, failed, skipped
    )

    return report


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "run":
        asyncio.run(run_audit())
    else:
        print("Usage: python -m reporium_audit run")


if __name__ == "__main__":
    main()
