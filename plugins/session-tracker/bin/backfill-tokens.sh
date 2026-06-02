#!/usr/bin/env bash
# Usage-only backfill for session-tracker-mcp.
# Walks every ~/.claude/projects/*/*.jsonl transcript and populates message_tokens.
# Idempotent (INSERT OR REPLACE on message_id) and pure-local: NO OpenAI key,
# no embeddings, no summaries, no network.
#
# Set SESSION_TRACKER_DB_PATH to dry-run against a throwaway copy of index.db
# instead of the live index.

set -euo pipefail

PKG_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." &> /dev/null && pwd)"

cd "$PKG_DIR"
exec bun -e '
import { backfillTokens } from "./src/indexer.ts";
console.log("[backfill-tokens] walking transcripts (usage only) …");
console.log(backfillTokens());
'
