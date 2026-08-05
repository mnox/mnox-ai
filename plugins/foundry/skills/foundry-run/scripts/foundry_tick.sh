#!/usr/bin/env bash
set -euo pipefail
cat >&2 <<'EOF'
foundry_tick.sh is decommissioned. Foundry/Peggy execution now routes through Sven's native Unit runtime:
  /Users/matt.noxon/dev/personal/sven/src-tauri/target/debug/sven_unit_workflow run --default-db --approve-local-write --enable-runtime-control --limit <n> --json
Do not use predecessor Foundry stores or scripts for new work.
EOF
exit 64
