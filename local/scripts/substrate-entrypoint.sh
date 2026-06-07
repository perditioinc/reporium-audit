#!/bin/sh
# nginx substrate entrypoint: ensure a self-signed cert exists, stamp a fresh
# reporium-db index.json (freshness gate is < 25h), then exec nginx.
set -eu

CERT_DIR=/etc/nginx/certs
CRT="$CERT_DIR/substrate.crt"
KEY="$CERT_DIR/substrate.key"

if [ ! -f "$CRT" ] || [ ! -f "$KEY" ]; then
    echo "[substrate] generating self-signed cert (SANs: reporium-api.local, api.github.com, raw.githubusercontent.com)"
    openssl req -x509 -newkey rsa:2048 -nodes \
        -keyout "$KEY" -out "$CRT" -days 365 \
        -subj "/CN=reporium-substrate" \
        -addext "subjectAltName=DNS:reporium-api.local,DNS:localhost,DNS:api.github.com,DNS:raw.githubusercontent.com"
    chmod 644 "$CRT"
fi

# Stamp index.json with a current timestamp so the freshness gate (< 25h) passes.
INDEX=/srv/raw/perditioinc/reporium-db/main/data/index.json
mkdir -p "$(dirname "$INDEX")"
NOW="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
cat > "$INDEX" <<EOF
{
  "meta": {
    "total": 120,
    "last_updated": "$NOW"
  }
}
EOF
echo "[substrate] stamped index.json last_updated=$NOW"

exec nginx -g 'daemon off;'
