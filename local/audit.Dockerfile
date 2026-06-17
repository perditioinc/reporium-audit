# OSS audit-runner image. Installs the audit's declared runtime deps only
# (httpx + python-dotenv). Source is mounted read-only at runtime, not COPYed,
# so the image never bakes a stale copy and the substrate stays purely additive
# to the repo.
FROM python:3.11-slim

RUN pip install --no-cache-dir "httpx>=0.27" "python-dotenv>=1.0"

WORKDIR /app
ENTRYPOINT ["/bin/sh", "-c"]
