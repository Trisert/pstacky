#!/usr/bin/env bash
# Clone cursor/plugins at the commit recorded in UPSTREAM_PIN, sparse to the
# subtrees pstacky ships. Idempotent: wipes and recreates vendor/cursor-plugins.
set -euo pipefail
cd "$(dirname "$0")/.."
sha=$(python3 -c 'import json; print(json.load(open("UPSTREAM_PIN"))["sha"])')
rm -rf vendor/cursor-plugins
git clone -q --filter=blob:none --no-checkout https://github.com/cursor/plugins vendor/cursor-plugins
git -C vendor/cursor-plugins sparse-checkout init --cone
git -C vendor/cursor-plugins sparse-checkout set pstack cursor-team-kit/skills/deslop
git -C vendor/cursor-plugins checkout -q "$sha"
echo "vendor: $(git -C vendor/cursor-plugins rev-parse HEAD)"
