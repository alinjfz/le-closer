#!/bin/sh
set -eu

# A named node_modules volume survives image rebuilds. Refresh it when the
# bind-mounted dependency manifests differ from the last successful install.
manifest_hash="$(sha256sum package.json package-lock.json | sha256sum | cut -d ' ' -f 1)"
marker="node_modules/.lecloser-dependencies.sha256"
installed_hash="$(cat "$marker" 2>/dev/null || true)"
if [ "$manifest_hash" != "$installed_hash" ]; then
  echo "Syncing frontend dependencies…"
  npm ci --no-audit --no-fund
  printf '%s\n' "$manifest_hash" > "$marker"
fi

exec npm run dev -- --host 0.0.0.0
