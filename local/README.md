# local/ — $0 OSS dev substrate for reporium-audit

Run the **real** audit (`python -m reporium_audit run`) end-to-end on your
machine against local open-source stand-ins for every cloud dependency. No GCP
credentials, no real GitHub token, no network calls to production. Additive and
local-only: nothing here touches prod, CI, or the audit source (mounted
read-only).

## Quick start

```bash
cd local
make up      # generate fixtures + .env, build, start nginx (waits healthy)
make smoke   # run the real audit against the substitutes; asserts zero FAILs
make down    # stop + remove containers, network, and volumes
```

Or from the repo root: `make local-up && make local-smoke && make local-down`.

Requires Docker + Docker Compose and `python3` (for fixture generation).

## Cloud dependency -> OSS substitute

The audit (dev branch) runs four check groups. Their external dependencies and
local substitutes:

| Audit dependency (real) | Surfaces used | OSS substitute | How it is wired |
|---|---|---|---|
| `reporium-api` (Cloud Run) | `/health`, `/repos`, `/search`, `/library/full` | `nginx` serving baked JSON | `REPORIUM_API_URL=https://reporium-api.local` (Docker network alias) |
| `api.github.com` (GitHub Actions API) | `/repos/<owner>/<repo>/actions/runs` for the active suite | same `nginx` | Docker network **alias** `api.github.com` + self-signed TLS trusted via `SSL_CERT_FILE` |
| `raw.githubusercontent.com` | reporium-db `data/index.json` | same `nginx` | Docker network **alias** `raw.githubusercontent.com` + `SSL_CERT_FILE` |

### Why TLS + DNS aliasing (and not a code change)

`REPORIUM_API_URL` is env-pointed, so the API surface is redirected with an env
var alone. But the GitHub hosts (`api.github.com`,
`raw.githubusercontent.com`) are **hardcoded** in the audit source
(`checks/workflows.py`, `checks/reporium_db.py`). Rather than patch the source,
the substrate:

1. gives the nginx container Docker **network aliases** for both hostnames, so
   DNS inside the compose network resolves them to the local nginx, and
2. serves a **self-signed cert** whose SANs cover both hosts, which the runner
   trusts via the standard `SSL_CERT_FILE` env var (honored by Python's `ssl`,
   which httpx uses).

The audit's real HTTPS request path runs completely unmodified.

## What the smoke proves

`make smoke` runs the actual `python -m reporium_audit run` inside the runner
container (audit source mounted read-only) and fails if the generated
`AUDIT_REPORT.md` contains any `FAIL` row. Every check's real code path is
exercised: the three reporium-api checks, the full `/library/full` data
contract, reporium-db freshness, and the GitHub Actions workflow status for all
twelve active-suite repos.

## Rehearsing a failure

The fixtures are plain JSON. To rehearse a regression locally, edit a fixture
and re-run `make smoke`. Examples:

- Flip a repo's `isPrivate` to `true` in `static/library_full.json` -> the
  "no private repos exposed" gate FAILs.
- Break a repo's `url` so it no longer ends with its `fullName` -> the
  "repo URLs match fullName" gate FAILs.
- Set a workflow run's `conclusion` to `failure` in
  `mock-api/repos/perditioinc/<repo>/actions/runs` -> that repo's CI gate FAILs.

## Files

- `docker-compose.yml` — substrate (nginx) + audit (runner) services.
- `nginx.conf` — routes for all three substituted hosts.
- `audit.Dockerfile` — runner image (httpx, python-dotenv).
- `scripts/gen_fixtures.py` — reporium-api fixtures.
- `scripts/gen_github_fixtures.py` — api.github.com + raw fixtures.
- `scripts/substrate-entrypoint.sh` — cert gen + fresh index.json stamp.
- `scripts/smoke.sh` — runs the real audit, asserts no failures.
- `.env.example` — local wiring (copied to `.env` by `make seed`).
