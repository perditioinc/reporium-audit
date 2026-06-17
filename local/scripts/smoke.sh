#!/bin/sh
# Smoke test: run the REAL audit (python -m reporium_audit run) inside the
# runner container against the local OSS substitutes, then assert the generated
# report has zero FAILs. Exercises every check's real code path (dev branch):
#   - reporium-api (/health, /repos, /search, /library/full)          via nginx
#   - api.github.com workflow runs for the active suite repos          via nginx
#   - raw.githubusercontent.com reporium-db index.json                 via nginx
set -eu

echo "[smoke] running: python -m reporium_audit run"
# Source is mounted read-only at /app/reporium_audit; expose it on PYTHONPATH.
# Run from a writable tmp dir so AUDIT_REPORT.md can be written.
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=/app
cd /tmp
python -m reporium_audit run

REPORT=/tmp/AUDIT_REPORT.md
if [ ! -f "$REPORT" ]; then
    echo "[smoke] FAIL: no AUDIT_REPORT.md produced"
    exit 1
fi

echo "[smoke] ---------- AUDIT_REPORT.md ----------"
cat "$REPORT"
echo "[smoke] -------------------------------------"

# Gate: any row with FAIL status fails the smoke. SKIP/WARN are acceptable.
if grep -q "✗ FAIL" "$REPORT"; then
    echo "[smoke] FAIL: report contains failing checks"
    exit 1
fi

echo "[smoke] PASS: no failing checks against the local OSS substitutes"
