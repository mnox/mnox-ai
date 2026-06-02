#!/usr/bin/env bash
# One-shot backfill for session-tracker-mcp.
# Re-indexes any new JSONL data, then catches up on missing embeddings + summaries.
# Uses OPENAI_API_KEY from the environment when set; otherwise runs FTS-only.

set -euo pipefail

PKG_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." &> /dev/null && pwd)"

if [ -z "${OPENAI_API_KEY:-}" ]; then
  echo "[backfill] no OPENAI_API_KEY in environment. FTS-only pass." >&2
fi
export OPENAI_API_KEY="${OPENAI_API_KEY:-}"

cd "$PKG_DIR"
exec bun -e '
import { indexAll, backfillEmbeddings, backfillSummaries } from "./src/indexer.ts";
console.log("[backfill] indexAll …");
console.log(await indexAll());
console.log("[backfill] backfillEmbeddings …");
console.log(await backfillEmbeddings());
console.log("[backfill] backfillSummaries …");
console.log(await backfillSummaries());
'
