"""Probe for stale Cloud Run candidate traffic tags on reporium-api.

Background
----------
Failed ``deploy.yml`` runs can leave ``candidate-*`` traffic tags
pointing at old revisions of the public ``reporium-api`` Cloud Run
service. PR #436 adds a cleanup step to the deploy workflow itself;
this check mirrors that from the audit side so we notice the drift
without GCP credentials.

Approach
--------
The Cloud Run admin API would give us the authoritative list of tags,
but that requires GCP credentials which aren't provisioned for the
audit CI runner. We use a credential-free fallback:

1. Ask GitHub (with ``GH_TOKEN``) for recent ``reporium-api`` workflow
   runs with "deploy" in the name.
2. Extract candidate tag names from run display names / head refs using
   a simple regex.
3. For each harvested tag, probe the tagged Cloud Run URL:
   ``https://<tag>---<service-root>/health``.
4. Compare the tag's ``/health`` revision to the untagged production
   ``/health`` revision. A tag whose revision differs from production
   *and* is reachable is a stale tag — flag it.

Limitations (documented — not silently hidden)
----------------------------------------------
- Tags created outside the recent-runs window are invisible from here.
- The ``reporium-api`` ``/health`` response must expose ``revision`` (or
  equivalent) for the comparison to work; missing field is reported as
  WARN, not PASS.
- Workflow run name parsing is heuristic. False negatives (tag
  not harvested) will fall through to the ``deploy.yml`` cleanup step.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

import httpx

# ``candidate-<sha-or-word>``, allowing alphanumerics and dashes.
CANDIDATE_TAG_RE = re.compile(r"candidate-[a-z0-9][a-z0-9-]{1,40}", re.IGNORECASE)

DEFAULT_DEPLOY_REPO = "perditioinc/reporium-api"


def _tagged_url(api_url: str, tag: str) -> str:
    """Return the Cloud Run tagged URL for ``tag`` given the base service URL.

    Cloud Run publishes tagged revisions under ``<tag>---<host>``, e.g.
    ``candidate-abc---reporium-api-573778300586.us-central1.run.app``.
    """
    parsed = urlparse(api_url)
    host = parsed.netloc or parsed.path
    # Strip any existing tag prefix so we anchor on the service root.
    if "---" in host:
        host = host.split("---", 1)[1]
    return f"{parsed.scheme or 'https'}://{tag}---{host}/health"


def _extract_revision(health_payload: dict | None) -> str | None:
    """Best-effort revision extraction from a ``/health`` JSON body.

    Looks at common field names so this doesn't need to be kept in
    lockstep with the API's schema — if a name changes the check stays
    useful (may degrade to WARN rather than FAIL).
    """
    if not isinstance(health_payload, dict):
        return None
    for key in ("revision", "k_revision", "service_revision", "version", "git_sha"):
        val = health_payload.get(key)
        if isinstance(val, str) and val:
            return val
    return None


async def _harvest_candidate_tags(
    client: httpx.AsyncClient, token: str, repo: str
) -> set[str]:
    """Pull recent deploy-workflow runs and extract candidate tag names."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    try:
        r = await client.get(
            f"https://api.github.com/repos/{repo}/actions/runs?per_page=30",
            headers=headers,
        )
        if r.status_code != 200:
            return set()
        runs = r.json().get("workflow_runs", [])
    except Exception:
        return set()

    tags: set[str] = set()
    for run in runs:
        name = (run.get("name") or "").lower()
        if "deploy" not in name:
            continue
        haystack = " ".join(
            str(run.get(k) or "") for k in ("name", "display_title", "head_branch")
        )
        for match in CANDIDATE_TAG_RE.findall(haystack):
            tags.add(match.lower())
    return tags


async def check_cloud_run_tags(
    api_url: str,
    token: str,
    deploy_repo: str = DEFAULT_DEPLOY_REPO,
) -> list[dict]:
    """Detect stale ``candidate-*`` Cloud Run traffic tags on reporium-api."""
    results: list[dict] = []

    if not api_url:
        results.append({
            "check": "cloud run candidate tags",
            "status": "SKIP",
            "detail": "REPORIUM_API_URL not set",
        })
        return results

    if not token:
        results.append({
            "check": "cloud run candidate tags",
            "status": "SKIP",
            "detail": "GH_TOKEN not set — can't harvest tag names",
        })
        return results

    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        # Production revision — the baseline we compare tagged probes to.
        try:
            prod = await client.get(f"{api_url}/health")
            prod_rev = _extract_revision(prod.json()) if prod.status_code == 200 else None
        except Exception as e:
            results.append({
                "check": "cloud run candidate tags",
                "status": "FAIL",
                "detail": f"production /health unreachable: {str(e)[:80]}",
            })
            return results

        tags = await _harvest_candidate_tags(client, token, deploy_repo)

        if not tags:
            results.append({
                "check": "cloud run candidate tags",
                "status": "PASS",
                "detail": "No candidate tags harvested from recent deploy runs",
            })
            return results

        if prod_rev is None:
            # Probe anyway, but we can only report reachability, not drift.
            results.append({
                "check": "cloud run candidate tags: revision field",
                "status": "WARN",
                "detail": "/health has no revision field — drift comparison degraded",
            })

        stale: list[str] = []
        unreachable: list[str] = []
        same_as_prod: list[str] = []

        for tag in sorted(tags):
            url = _tagged_url(api_url, tag)
            try:
                r = await client.get(url, timeout=10)
            except Exception:
                unreachable.append(tag)
                continue

            if r.status_code != 200:
                unreachable.append(tag)
                continue

            try:
                tag_rev = _extract_revision(r.json())
            except Exception:
                tag_rev = None

            if prod_rev and tag_rev and tag_rev != prod_rev:
                stale.append(f"{tag} ({tag_rev} != {prod_rev})")
            elif prod_rev and tag_rev and tag_rev == prod_rev:
                same_as_prod.append(tag)
            else:
                # Reachable but revision unknown — treat as suspect WARN.
                stale.append(f"{tag} (revision unknown)")

        detail = (
            f"{len(tags)} tag(s) harvested; stale={len(stale)}, "
            f"same-as-prod={len(same_as_prod)}, unreachable={len(unreachable)}"
        )
        if stale:
            detail += f". Stale: {stale[:5]}"

        results.append({
            "check": "cloud run candidate tags",
            "status": "FAIL" if stale else "PASS",
            "detail": detail,
        })

    return results
