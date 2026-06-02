#!/usr/bin/env bun
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { loadOverlays, saveOverlays, upsertOverlay, removeStaleOverlays, formatAge } from './storage.js';
import { reconcile, findSession } from './reconciler.js';
import {
  SessionListInputSchema,
  SessionGetInputSchema,
  SessionUpdateInputSchema,
  SessionCleanupInputSchema,
  SessionSearchInputSchema,
  SessionTokenStatsInputSchema,
  SetSessionLabelInputSchema,
  AgentChangesInputSchema,
  SessionConfigGetInputSchema,
  SessionConfigSetInputSchema,
  type AgentSession,
} from './types.js';
import { getConfig, setConfig } from './config.js';
import { getDb } from './db.js';
import {
  getSessionContext,
  getChangeSetCount,
  listChangeSets,
  listFileChanges,
  type ChangeSetRow,
  type FileChangeRow,
} from './change-tracker.js';
import type { AgentChangesFilters } from './change-tracker.js';
import { searchSessions } from './search.js';
import { getPresence, setTabLabel } from './presence.js';
import { ownTtyDevice, deriveRepo, writeTabTitle, formatTabTitle, logTabDebug } from './tab-title.js';

const SERVER_INSTRUCTIONS =
  'This server searches your past agent sessions. By DEFAULT search is LEXICAL only ' +
  '(FTS5 keyword matching) — zero network calls, zero cost. Richer SEMANTIC (embeddings) ' +
  'search is available but OFF by default. On the first time semantic search would help a ' +
  'user request, call session_config_get. IF embeddings.prompted is false, ask the user ONCE ' +
  'whether to enable semantic search, explaining it requires EITHER an OPENAI_API_KEY (sends ' +
  'session text to OpenAI, has cost) OR a fully-local embedder at ONS_EMBED_URL (no egress, no ' +
  'cost). Then record the outcome with session_config_set: ALWAYS set prompted:true, and set ' +
  'enabled/mode per their answer (mode "openai" or "local" to enable, "off" to decline). IF ' +
  'embeddings.prompted is already true, NEVER ask again.';

const server = new McpServer({
  name: 'session-tracker-mcp',
  version: '0.1.0',
}, {
  instructions: SERVER_INSTRUCTIONS,
});

const SOURCE_ICONS: Record<string, string> = {
  claude: 'C',
  cursor: 'Cu',
  codex: 'Cx',
};

/** Group digits with thousands separators (locale-independent). */
function fmtN(n: number): string {
  return Math.round(n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

function statusIcon(session: AgentSession): string {
  switch (session.status) {
    case 'active':
      return '🟢';
    case 'idle':
      return '😴';
    case 'completed':
      return '✅';
    default:
      return '💀';
  }
}

function formatSessionMarkdown(session: AgentSession): string {
  const lines: string[] = [];

  lines.push(`## ${statusIcon(session)} ${session.title || session.projectName} [${session.shortId}]`);
  lines.push('');
  lines.push(`**Source:** ${session.source}`);
  lines.push(`**Project:** ${session.projectName}`);
  if (session.cwd) lines.push(`**Directory:** ${session.cwd}`);
  if (session.branch) lines.push(`**Branch:** ${session.branch}`);
  if (session.model) lines.push(`**Model:** ${session.model}`);
  lines.push(`**Status:** ${session.status}`);
  lines.push('');
  lines.push(`**Started:** ${formatAge(session.startedAt)}`);
  lines.push(`**Last Activity:** ${formatAge(session.lastActivityAt)}`);
  if (session.endedAt) lines.push(`**Ended:** ${formatAge(session.endedAt)}`);
  lines.push('');
  lines.push(
    `**Messages:** ${session.messageCount} | **Tools:** ${session.toolCalls} | **Agents:** ${session.agentsSpawned}`
  );
  if (session.totalTokens > 0) {
    lines.push(
      `**Tokens:** ${fmtN(session.totalTokens)} total ` +
        `(in ${fmtN(session.inputTokens)} · out ${fmtN(session.outputTokens)} · ` +
        `cache-w ${fmtN(session.cacheCreationTokens)} · cache-r ${fmtN(session.cacheReadTokens)})`
    );
  }

  if (session.summary) {
    lines.push('');
    lines.push(`**Summary:** ${session.summary}`);
  }
  if (session.firstPrompt) {
    lines.push(`**First Prompt:** ${session.firstPrompt}`);
  }

  if (session.tags.length > 0) {
    lines.push(`**Tags:** ${session.tags.map((t) => `\`${t}\``).join(', ')}`);
  }
  if (session.notes) {
    lines.push('');
    lines.push(`**Notes:** ${session.notes}`);
  }

  return lines.join('\n');
}

function formatSessionRow(session: AgentSession): string {
  const age = formatAge(session.lastActivityAt);
  const title = session.title || session.projectName;
  const truncatedTitle = title.length > 30 ? title.slice(0, 27) + '...' : title;
  const src = SOURCE_ICONS[session.source] ?? session.source;

  return `| ${statusIcon(session)} | \`${session.shortId}\` | ${src} | ${truncatedTitle} | ${session.messageCount} | ${age} |`;
}

server.registerTool(
  'session_list',
  {
    title: 'List Sessions',
    description: `List agent sessions with optional filtering.

Args:
  - status: Filter by "active" | "idle" | "completed" | "abandoned" | "all" (default: "all")
  - source: Filter by "claude" | "cursor" | "codex" | "all" (default: "all")
  - project: Filter by project name (partial match)
  - since: ISO 8601 date/datetime — only sessions with lastActivityAt >= since
  - until: ISO 8601 date/datetime — only sessions with lastActivityAt <= until
  - limit: Max results 1-100 (default: 20)
  - format: "markdown" | "json" (default: "markdown")

Returns:
  List of sessions sorted by last activity (most recent first).
  Shows shortId, project, status, and activity counts.`,
    inputSchema: SessionListInputSchema,
    annotations: {
      readOnlyHint: true,
      destructiveHint: false,
      idempotentHint: true,
      openWorldHint: false,
    },
  },
  async ({ status, source, project, since, until, limit, format }) => {
    let sessions = reconcile();

    if (status !== 'all') {
      sessions = sessions.filter((s) => s.status === status);
    }

    if (source !== 'all') {
      sessions = sessions.filter((s) => s.source === source);
    }

    if (project) {
      const lower = project.toLowerCase();
      sessions = sessions.filter(
        (s) => s.projectName.toLowerCase().includes(lower) || s.cwd.toLowerCase().includes(lower)
      );
    }

    if (since) {
      const sinceMs = Date.parse(since);
      if (Number.isNaN(sinceMs)) {
        return { isError: true, content: [{ type: 'text' as const, text: `Invalid \`since\` date: "${since}". Use ISO 8601 (e.g. "2026-05-01").` }] };
      }
      sessions = sessions.filter((s) => Date.parse(s.lastActivityAt) >= sinceMs);
    }

    if (until) {
      const untilMs = Date.parse(until);
      if (Number.isNaN(untilMs)) {
        return { isError: true, content: [{ type: 'text' as const, text: `Invalid \`until\` date: "${until}". Use ISO 8601 (e.g. "2026-05-01").` }] };
      }
      sessions = sessions.filter((s) => Date.parse(s.lastActivityAt) <= untilMs);
    }

    sessions = sessions.slice(0, limit);

    if (sessions.length === 0) {
      return { content: [{ type: 'text' as const, text: 'No sessions found matching the criteria.' }] };
    }

    if (format === 'json') {
      return { content: [{ type: 'text' as const, text: JSON.stringify(sessions, null, 2) }] };
    }

    const lines = [
      `# Sessions (${sessions.length}${status !== 'all' ? ` ${status}` : ''}${source !== 'all' ? ` ${source}` : ''})`,
      '',
      '| Status | ID | Src | Project | Msgs | Last Activity |',
      '|--------|----|-----|---------|------|---------------|',
      ...sessions.map(formatSessionRow),
    ];

    return { content: [{ type: 'text' as const, text: lines.join('\n') }] };
  }
);

server.registerTool(
  'session_get',
  {
    title: 'Get Session Details',
    description: `Get full details for a specific session.

Args:
  - id: Session ID (full UUID or 8-char shortId)

Returns:
  Complete session information including stats, notes, and tags.`,
    inputSchema: SessionGetInputSchema,
    annotations: {
      readOnlyHint: true,
      destructiveHint: false,
      idempotentHint: true,
      openWorldHint: false,
    },
  },
  async ({ id }) => {
    const sessions = reconcile();
    const session = findSession(sessions, id);
    if (!session) {
      return {
        isError: true,
        content: [{ type: 'text' as const, text: `Session "${id}" not found.` }],
      };
    }

    const changeSetCount = getChangeSetCount(session.id);
    const foundation = getSessionContext(session.id);

    const lines: string[] = [formatSessionMarkdown(session)];
    lines.push('');
    lines.push(`**Changes:** ${changeSetCount} change-set${changeSetCount !== 1 ? 's' : ''}`);
    if (foundation) {
      const parts: string[] = [];
      if (foundation.branch) parts.push(`branch=${foundation.branch}`);
      if (foundation.pr_number) parts.push(`pr=${foundation.pr_number}`);
      if (foundation.shipyard_task) parts.push(`task=${foundation.shipyard_task}`);
      if (parts.length > 0) {
        lines.push(`**Context:** ${parts.join(' ')}`);
      }
    }

    return { content: [{ type: 'text' as const, text: lines.join('\n') }] };
  }
);

server.registerTool(
  'session_update',
  {
    title: 'Update Session',
    description: `Update session metadata or status.

Args:
  - id: Session ID (optional - defaults to matching current cwd if omitted)
  - title: Human-readable session title
  - tags: Array of tags like ["bug", "feature"]
  - notes: Freeform notes about the session
  - status: Only "completed" is allowed (to end a session)

Returns:
  Updated session details.`,
    inputSchema: SessionUpdateInputSchema,
    annotations: {
      readOnlyHint: false,
      destructiveHint: false,
      idempotentHint: true,
      openWorldHint: false,
    },
  },
  async ({ id, title, tags, notes, status }) => {
    const sessions = reconcile();

    let session: AgentSession | undefined;
    if (id) {
      session = findSession(sessions, id);
    } else {
      const cwd = process.cwd();
      session = sessions.find((s) => s.cwd === cwd && s.status === 'active');
    }

    if (!session) {
      return {
        isError: true,
        content: [
          {
            type: 'text' as const,
            text: id ? `Session "${id}" not found.` : 'No active session found for current directory.',
          },
        ],
      };
    }

    const overlays = loadOverlays();
    const updates: { title?: string; tags?: string[]; notes?: string } = {};
    if (title !== undefined) updates.title = title;
    if (tags !== undefined) updates.tags = tags;
    if (notes !== undefined) updates.notes = notes;

    if (Object.keys(updates).length > 0) {
      upsertOverlay(overlays, session.id, session.source, updates);
      saveOverlays(overlays);
    }

    if (title !== undefined) session.title = title;
    if (tags !== undefined) session.tags = tags;
    if (notes !== undefined) session.notes = notes;
    if (status === 'completed') {
      session.status = 'completed';
      session.endedAt = new Date().toISOString();
    }

    return { content: [{ type: 'text' as const, text: formatSessionMarkdown(session) }] };
  }
);

server.registerTool(
  'session_cleanup',
  {
    title: 'Cleanup Sessions',
    description: `Archive old/abandoned sessions.

Args:
  - older_than_days: Archive sessions older than N days (default: 7)
  - dry_run: Preview without archiving (default: true)

Returns:
  List of sessions that would be/were archived.`,
    inputSchema: SessionCleanupInputSchema,
    annotations: {
      readOnlyHint: false,
      destructiveHint: true,
      idempotentHint: false,
      openWorldHint: false,
    },
  },
  async ({ older_than_days, dry_run }) => {
    const sessions = reconcile();
    const cutoff = Date.now() - older_than_days * 24 * 60 * 60 * 1000;

    const stale = sessions.filter((s) => {
      const lastActivity = new Date(s.lastActivityAt).getTime();
      return lastActivity < cutoff && s.status !== 'active';
    });

    if (stale.length === 0) {
      return {
        content: [{ type: 'text' as const, text: `No sessions older than ${older_than_days} days to clean up.` }],
      };
    }

    if (dry_run) {
      const lines = [
        `# Dry Run: Would remove overlays for ${stale.length} stale sessions`,
        '',
        ...stale.map(
          (s) =>
            `- \`${s.shortId}\` [${s.source}] ${s.projectName} (${s.status}, last active ${formatAge(s.lastActivityAt)})`
        ),
        '',
        'Run with dry_run=false to remove stale overlays.',
      ];
      return { content: [{ type: 'text' as const, text: lines.join('\n') }] };
    }

    const overlays = loadOverlays();
    const validIds = new Set(sessions.filter((s) => !stale.includes(s)).map((s) => `${s.source}:${s.id}`));
    const removed = removeStaleOverlays(overlays, validIds);
    saveOverlays(overlays);

    const lines = [
      `# Cleaned up ${removed.length} stale overlays`,
      '',
      ...removed.map((o) => `- \`${o.id.slice(0, 8)}\` [${o.source}]`),
    ];

    return { content: [{ type: 'text' as const, text: lines.join('\n') }] };
  }
);

server.registerTool(
  'session_search',
  {
    title: 'Search Sessions',
    description: `Full-text + semantic search across past Claude Code sessions.

Args:
  - query: Words/phrases you remember from the session
  - mode: "lexical" | "semantic" | "hybrid" (default: hybrid — fuses FTS and embeddings)
  - scope: "chunks" | "summaries" | "both" (default: both)
  - project: Filter by project name (partial match)
  - since_days: Restrict to sessions active in the last N days (ignored if \`since\` is provided)
  - since: ISO 8601 date/datetime — only hits with ts >= since (takes precedence over since_days)
  - until: ISO 8601 date/datetime — only hits with ts <= until
  - limit: Max sessions returned 1-50 (default: 10)

Returns:
  Ranked list of sessions with snippets and shortIds. Use shortIds with session_get for full detail.`,
    inputSchema: SessionSearchInputSchema,
    annotations: {
      readOnlyHint: true,
      destructiveHint: false,
      idempotentHint: true,
      openWorldHint: false,
    },
  },
  async ({ query, mode, scope, project, since_days, since, until, limit }) => {
    let sinceMs: number | undefined;
    if (since) {
      const ms = Date.parse(since);
      if (Number.isNaN(ms)) {
        return { isError: true, content: [{ type: 'text' as const, text: `Invalid \`since\` date: "${since}". Use ISO 8601.` }] };
      }
      sinceMs = ms;
    } else if (since_days) {
      sinceMs = Date.now() - since_days * 24 * 60 * 60 * 1000;
    }

    let untilMs: number | undefined;
    if (until) {
      const ms = Date.parse(until);
      if (Number.isNaN(ms)) {
        return { isError: true, content: [{ type: 'text' as const, text: `Invalid \`until\` date: "${until}". Use ISO 8601.` }] };
      }
      untilMs = ms;
    }

    const hits = await searchSessions({ query, mode, scope, project, since: sinceMs, until: untilMs, limit });

    if (hits.length === 0) {
      return { content: [{ type: 'text' as const, text: `No sessions found matching "${query}".` }] };
    }

    const lines = [`# Search results for "${query}" (${hits.length})`, ''];
    for (const h of hits) {
      const shortId = h.session_id.slice(0, 8);
      const proj = h.project ?? 'unknown';
      const when = formatAge(new Date(h.ts).toISOString());
      const presence = getPresence(h.session_id);
      const presenceTag =
        presence?.status === 'live' ? '🟢 live' : presence?.status === 'ended' ? '⚫ ended' : '❔ unknown';
      const link = `[open](clatab://${shortId})`;
      lines.push(`### \`${shortId}\` — ${proj} ${link} _(${presenceTag}, ${when}, via ${h.source})_`);
      lines.push(h.snippet.replace(/\s+/g, ' ').trim());
      lines.push('');
    }

    return { content: [{ type: 'text' as const, text: lines.join('\n') }] };
  }
);

server.registerTool(
  'set_session_label',
  {
    title: 'Set Session Label',
    description: `Rename this session's Warp tab to "[REPO] label" (repo uppercased and bracketed).

Args:
  - label: 2–3 word descriptor for the current task (e.g. "add auth middleware")

Behavior:
  - Writes OSC 2 escape to this server's OWN controlling tty (always the caller's tab).
  - Persists the label keyed by that tty, so the stop hook re-asserts the title
    after every prompt and it survives session_id churn (resume/compaction).
  - No-ops silently on non-Warp terminals or when the tty device is unavailable.
  - repo is derived from git toplevel of cwd (or basename of cwd as fallback).`,
    inputSchema: SetSessionLabelInputSchema,
    annotations: {
      readOnlyHint: false,
      destructiveHint: false,
      idempotentHint: true,
      openWorldHint: false,
    },
  },
  async ({ label }) => {
    const tty = ownTtyDevice();
    const repo = deriveRepo(process.cwd());
    const title = formatTabTitle(repo, label);

    const result = writeTabTitle(tty, title); // silent no-op on non-Warp / no-tty
    logTabDebug('set_session_label', result, { tty, title });

    // Persist keyed by tty so the stop-hook re-assert re-writes the same title
    // every turn — immune to session_id churn on resume/compaction.
    if (tty) {
      setTabLabel(tty, label);
    }

    const lines: string[] = [`Tab title set: **${title}**`];
    if (!result.ok) lines.push('(non-Warp terminal or no tty — title write skipped)');

    return { content: [{ type: 'text' as const, text: lines.join('\n') }] };
  }
);

server.registerTool(
  'agent_changes',
  {
    title: 'Agent Changes',
    description: `Query the file-change paper trail — change-sets and their file changes, with rationale.

Args:
  - session_id: Full UUID, sidechain id, or 8-char shortId (omit for cross-session)
  - since: ISO 8601 — only change_sets with ts_start >= since
  - until: ISO 8601 — only change_sets with ts_start <= until
  - file_path: Substring match on file_changes.file_path
  - branch: Exact match on change_sets.branch
  - pr: Match change_sets.pr_number
  - shipyard_task: e.g. "CX-160" — match change_sets.shipyard_task
  - limit: Max change_sets 1-100 (default: 25)
  - format: "markdown" | "json" (default: "markdown")

Returns:
  Change-sets with their file changes, rationale lines, and enrichment (branch/PR/task).`,
    inputSchema: AgentChangesInputSchema,
    annotations: {
      readOnlyHint: true,
      destructiveHint: false,
      idempotentHint: true,
      openWorldHint: false,
    },
  },
  async ({ session_id, since, until, file_path, branch, pr, shipyard_task, limit, format }) => {
    // Resolve since/until to epoch-ms (mirror session_search pattern)
    let sinceMs: number | undefined;
    if (since) {
      const ms = Date.parse(since);
      if (Number.isNaN(ms)) {
        return { isError: true, content: [{ type: 'text' as const, text: `Invalid \`since\` date: "${since}". Use ISO 8601.` }] };
      }
      sinceMs = ms;
    }

    let untilMs: number | undefined;
    if (until) {
      const ms = Date.parse(until);
      if (Number.isNaN(ms)) {
        return { isError: true, content: [{ type: 'text' as const, text: `Invalid \`until\` date: "${until}". Use ISO 8601.` }] };
      }
      untilMs = ms;
    }

    // Resolve shortId → full session id when needed
    let resolvedSessionId: string | undefined;
    if (session_id) {
      const sessions = reconcile();
      const found = findSession(sessions, session_id);
      resolvedSessionId = found?.id ?? session_id;
    }

    const filters: AgentChangesFilters = {
      session_id: resolvedSessionId,
      since: sinceMs,
      until: untilMs,
      file_path,
      branch,
      pr,
      shipyard_task,
      limit,
    };

    const changeSets = listChangeSets(filters);
    const ids = changeSets.map((cs) => cs.id);
    const filesBySet = listFileChanges(ids);

    interface AgentChangesResult {
      change_sets: Array<ChangeSetRow & { files: FileChangeRow[] }>;
      total: number;
    }

    if (format === 'json') {
      const result: AgentChangesResult = {
        change_sets: changeSets.map((cs) => ({ ...cs, files: filesBySet[cs.id] ?? [] })),
        total: changeSets.length,
      };
      return { content: [{ type: 'text' as const, text: JSON.stringify(result, null, 2) }] };
    }

    // Markdown output
    if (changeSets.length === 0) {
      return { content: [{ type: 'text' as const, text: 'No change-sets found matching the criteria.' }] };
    }

    const lines: string[] = [`# Change-sets (${changeSets.length})`, ''];
    for (const cs of changeSets) {
      const files = filesBySet[cs.id] ?? [];
      const heading = cs.shipyard_task ?? cs.branch ?? new Date(cs.ts_start).toISOString();
      lines.push(`### ${heading} — ${files.length} file${files.length !== 1 ? 's' : ''}`);
      if (cs.rationale) lines.push(`_${cs.rationale}_`);
      if (cs.trigger_user_prompt) lines.push(`**Prompt:** ${cs.trigger_user_prompt.slice(0, 120)}`);
      for (const fc of files) {
        lines.push(`- \`${fc.tool_name}\` ${fc.file_path ?? '(no path)'}`);
      }
      lines.push('');
    }

    return { content: [{ type: 'text' as const, text: lines.join('\n') }] };
  }
);

interface TokenTotalsRow {
  sessions: number;
  messages: number;
  input: number;
  output: number;
  cache_creation: number;
  cache_read: number;
}

interface TokenBreakdownRow {
  key: string | null;
  input: number;
  output: number;
  cache_creation: number;
  cache_read: number;
  total: number;
}

server.registerTool(
  'session_token_stats',
  {
    title: 'Session Token Stats',
    description: `Aggregate token usage across sessions — the lifetime "how much have I spent" view.

Sums the four token buckets (input / output / cache-write / cache-read) recorded per
assistant message. Subagent sessions are counted (they consume real tokens). NOTE: these
are RAW token counts, not dollars — subscription usage isn't metered, so treat the total
as "tokens processed", not a bill.

Args:
  - project: Filter by project name (partial match)
  - since: ISO 8601 — only usage with ts >= since (e.g. "2026-01-01")
  - until: ISO 8601 — only usage with ts <= until
  - group_by: "model" | "project" | "both" | "none" (default: both)
  - format: "markdown" | "json" (default: "markdown")

Returns:
  Grand total plus optional per-model and per-project breakdowns.`,
    inputSchema: SessionTokenStatsInputSchema,
    annotations: {
      readOnlyHint: true,
      destructiveHint: false,
      idempotentHint: true,
      openWorldHint: false,
    },
  },
  async ({ project, since, until, group_by, format }) => {
    let sinceMs: number | undefined;
    if (since) {
      const ms = Date.parse(since);
      if (Number.isNaN(ms)) {
        return { isError: true, content: [{ type: 'text' as const, text: `Invalid \`since\` date: "${since}". Use ISO 8601.` }] };
      }
      sinceMs = ms;
    }
    let untilMs: number | undefined;
    if (until) {
      const ms = Date.parse(until);
      if (Number.isNaN(ms)) {
        return { isError: true, content: [{ type: 'text' as const, text: `Invalid \`until\` date: "${until}". Use ISO 8601.` }] };
      }
      untilMs = ms;
    }

    const conds: string[] = [];
    const params: Array<string | number> = [];
    if (project) {
      conds.push('project LIKE ?');
      params.push(`%${project}%`);
    }
    if (sinceMs !== undefined) {
      conds.push('ts >= ?');
      params.push(sinceMs);
    }
    if (untilMs !== undefined) {
      conds.push('ts <= ?');
      params.push(untilMs);
    }
    const baseWhere = conds.length > 0 ? `WHERE ${conds.join(' AND ')}` : '';

    const db = getDb();
    const totals = db
      .query<TokenTotalsRow, Array<string | number>>(
        `SELECT COUNT(DISTINCT session_id)               AS sessions,
                COUNT(*)                                  AS messages,
                COALESCE(SUM(input_tokens), 0)            AS input,
                COALESCE(SUM(output_tokens), 0)           AS output,
                COALESCE(SUM(cache_creation_tokens), 0)   AS cache_creation,
                COALESCE(SUM(cache_read_tokens), 0)       AS cache_read
         FROM message_tokens ${baseWhere}`
      )
      .get(...params) as TokenTotalsRow;

    const wantModel = group_by === 'model' || group_by === 'both';
    const wantProject = group_by === 'project' || group_by === 'both';

    const breakdown = (keyCol: string, extraConds: string[]): TokenBreakdownRow[] => {
      const where = [...conds, ...extraConds];
      const whereSql = where.length > 0 ? `WHERE ${where.join(' AND ')}` : '';
      return db
        .query<TokenBreakdownRow, Array<string | number>>(
          `SELECT ${keyCol}                                AS key,
                  COALESCE(SUM(input_tokens), 0)            AS input,
                  COALESCE(SUM(output_tokens), 0)           AS output,
                  COALESCE(SUM(cache_creation_tokens), 0)   AS cache_creation,
                  COALESCE(SUM(cache_read_tokens), 0)       AS cache_read,
                  COALESCE(SUM(input_tokens + output_tokens + cache_creation_tokens + cache_read_tokens), 0) AS total
           FROM message_tokens ${whereSql}
           GROUP BY ${keyCol}
           ORDER BY total DESC`
        )
        .all(...params);
    };

    const byModel = wantModel ? breakdown('model', ["model IS NOT NULL", "model != '<synthetic>'"]) : [];
    const byProject = wantProject ? breakdown('project', ['project IS NOT NULL']) : [];

    const grandTotal = totals.input + totals.output + totals.cache_creation + totals.cache_read;

    if (format === 'json') {
      return {
        content: [
          {
            type: 'text' as const,
            text: JSON.stringify(
              {
                filters: { project: project ?? null, since: since ?? null, until: until ?? null },
                totals: { ...totals, total: grandTotal },
                byModel,
                byProject,
              },
              null,
              2
            ),
          },
        ],
      };
    }

    if (totals.messages === 0) {
      return { content: [{ type: 'text' as const, text: 'No token usage recorded for the given filters.' }] };
    }

    const filterBits: string[] = [];
    if (project) filterBits.push(`project~"${project}"`);
    if (since) filterBits.push(`since ${since}`);
    if (until) filterBits.push(`until ${until}`);
    const filterSuffix = filterBits.length > 0 ? ` _(${filterBits.join(', ')})_` : ' (lifetime)';

    const lines: string[] = [
      `# Token usage${filterSuffix}`,
      '',
      `**${fmtN(grandTotal)} tokens** across ${fmtN(totals.sessions)} session${totals.sessions !== 1 ? 's' : ''} / ${fmtN(totals.messages)} assistant messages`,
      '',
      `- input: ${fmtN(totals.input)}`,
      `- output: ${fmtN(totals.output)}`,
      `- cache write: ${fmtN(totals.cache_creation)}`,
      `- cache read: ${fmtN(totals.cache_read)}`,
      '',
      `_Raw token counts — not dollars. Subagent usage included._`,
    ];

    const renderTable = (title: string, rows: TokenBreakdownRow[]) => {
      if (rows.length === 0) return;
      lines.push('', `## By ${title}`, '', '| ' + title + ' | total | in | out | cache-w | cache-r |', '|---|---|---|---|---|---|');
      for (const r of rows) {
        lines.push(
          `| ${r.key ?? '(none)'} | ${fmtN(r.total)} | ${fmtN(r.input)} | ${fmtN(r.output)} | ${fmtN(r.cache_creation)} | ${fmtN(r.cache_read)} |`
        );
      }
    };
    if (wantModel) renderTable('model', byModel);
    if (wantProject) renderTable('project', byProject);

    return { content: [{ type: 'text' as const, text: lines.join('\n') }] };
  }
);

server.registerTool(
  'session_config_get',
  {
    title: 'Get Session-Tracker Config',
    description: `Read the session-tracker config — the embeddings/semantic-search opt-in state.

Args: none.

Returns:
  The embeddings block: { enabled, mode, prompted }.
  - enabled: master switch for semantic features (default false)
  - mode: "off" | "openai" | "local"
  - prompted: whether the user has already been asked once about enabling semantic search

Semantic search is OFF by default — search is lexical (FTS5) only, with zero network
calls and zero cost until explicitly enabled here.`,
    inputSchema: SessionConfigGetInputSchema,
    annotations: {
      readOnlyHint: true,
      destructiveHint: false,
      idempotentHint: true,
      openWorldHint: false,
    },
  },
  async () => {
    const { embeddings } = getConfig();
    return { content: [{ type: 'text' as const, text: JSON.stringify({ embeddings }, null, 2) }] };
  }
);

server.registerTool(
  'session_config_set',
  {
    title: 'Set Session-Tracker Config',
    description: `Update the embeddings/semantic-search opt-in config and persist it.

Args (all optional — only provided keys are changed):
  - enabled: boolean — master switch for semantic features
  - mode: "off" | "openai" | "local"
      • "openai" uses OPENAI_API_KEY (sends session text to OpenAI, has cost)
      • "local" uses a local embedder at ONS_EMBED_URL (no egress, no cost)
      • "off" disables semantic search (lexical FTS only)
  - prompted: boolean — set true once the user has been asked about enabling semantic search

Returns:
  The new embeddings config.`,
    inputSchema: SessionConfigSetInputSchema,
    annotations: {
      readOnlyHint: false,
      destructiveHint: false,
      idempotentHint: true,
      openWorldHint: false,
    },
  },
  async ({ enabled, mode, prompted }) => {
    const { embeddings } = setConfig({ enabled, mode, prompted });
    return { content: [{ type: 'text' as const, text: JSON.stringify({ embeddings }, null, 2) }] };
  }
);

async function main(): Promise<void> {
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch((error: unknown) => {
  console.error('Server error:', error);
  process.exit(1);
});
