# session-tracker

A local **MCP server** that indexes and searches your AI coding-agent sessions —
Claude Code, Cursor, and Codex — so you can ask "what was I working on yesterday?",
search across past sessions, label the current one, and inspect the file-change
trail of any session.

Everything runs **on your machine**. Search is **lexical (SQLite FTS5) by default**
— no network calls, no API key, no cost. Richer **semantic search is opt-in** and
the server asks you once before enabling it.

## Requirements

- [**Bun**](https://bun.sh) on your `PATH` (`brew install oven-sh/bun/bun`). The
  server is TypeScript run directly by Bun and uses Bun's built-in SQLite.
- Claude Code (the hooks and MCP wiring are installed by the plugin).

Dependencies are installed automatically on first launch (`bun install`), so no
manual build step is needed.

## Install

From the `mnox-ai` marketplace:

```
/plugin marketplace add mnox/mnox-ai
/plugin install session-tracker@mnox-ai
```

That registers the MCP server and three session-lifecycle hooks
(`SessionStart`, `SessionEnd`, `Stop`).

## How it works

- **Hooks** record session presence and, on each `Stop`, index the session's
  transcript into a local SQLite database.
- **Storage** lives at `~/.claude/sessions/index.db` (override with
  `SESSION_TRACKER_DB_PATH`). Logs go to `~/.claude/sessions/logs/`.
- **Search** is full-text by default. If you opt into semantic search, the indexer
  additionally computes embeddings (and optional summaries) and `session_search`
  fuses lexical + vector results.

## MCP tools

| Tool | Description |
|---|---|
| `session_list` | List agent sessions with optional status / source / project / date filtering. |
| `session_get` | Get full details for a specific session by ID or 8-char shortId. |
| `session_update` | Update a session's title, tags, notes, or mark it completed. |
| `session_cleanup` | Archive/remove overlays for old or abandoned sessions (dry-run by default). |
| `session_search` | Full-text (and, when enabled, semantic) search across past sessions. |
| `set_session_label` | Rename the current session's terminal tab to `[REPO] label`. |
| `agent_changes` | Query the file-change paper trail (change-sets, file changes, rationale). |
| `session_token_stats` | Aggregate lifetime token usage with per-model / per-project breakdowns. |
| `session_config_get` | Read the semantic-search opt-in config (`{ enabled, mode, prompted }`). |
| `session_config_set` | Update and persist that config (`enabled` / `mode` / `prompted`). |

## Semantic search (opt-in)

By default `embeddings.enabled` is `false` — pure lexical search, zero egress. The
server's instructions prompt your agent to offer semantic search **once**; you can
also enable it explicitly via the `session_config_set` tool:

- **Local embedder (no egress, no cost):**
  `session_config_set { enabled: true, mode: "local" }` — calls an embedder at
  `ONS_EMBED_URL` (default `http://127.0.0.1:9001/embed`).
- **OpenAI (sends session text to OpenAI, has cost):**
  `session_config_set { enabled: true, mode: "openai" }` — uses `OPENAI_API_KEY`
  from the environment. Summaries require this mode.
- **Off:** `session_config_set { enabled: false }` (or `mode: "off"`).

If semantic mode is enabled but the chosen backend is unreachable or unconfigured,
search **degrades gracefully to lexical** rather than failing.

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `SESSION_TRACKER_DB_PATH` | `~/.claude/sessions/index.db` | SQLite database location. |
| `OPENAI_API_KEY` | _(unset)_ | Only used when semantic `mode` is `openai`. Never read otherwise. |
| `ONS_EMBED_URL` | `http://127.0.0.1:9001/embed` | Local embedder endpoint when `mode` is `local`. |

## Maintenance scripts

- `bin/backfill.sh` — re-index new transcripts and, if semantic search is enabled,
  catch up on missing embeddings/summaries. FTS-only when disabled.
- `bin/backfill-tokens.sh` — backfill per-message token usage only (no key, no
  network).

## Privacy

No session text leaves your machine unless you explicitly enable `mode: "openai"`.
Lexical search, indexing, presence tracking, labels, and token stats are all
fully local. The session database is local to your home directory and is never
part of this repository.
