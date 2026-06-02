import { getDb } from '../db.js';
import type { AgentSession, SessionStatus } from '../types.js';

const IDLE_MS = 30 * 60 * 1000;
const ABANDONED_MS = 2 * 60 * 60 * 1000;

interface AggregateRow {
  session_id: string;
  project: string | null;
  message_count: number;
  started_ms: number;
  last_ms: number;
  summary: string | null;
  cwd: string | null;
  input_tokens: number;
  output_tokens: number;
  cache_creation_tokens: number;
  cache_read_tokens: number;
}

interface ModelRow {
  session_id: string;
  model: string | null;
}

interface FirstPromptRow {
  session_id: string;
  content: string;
}

function deriveStatus(lastMs: number): SessionStatus {
  const elapsed = Date.now() - lastMs;
  if (elapsed >= ABANDONED_MS) return 'abandoned';
  if (elapsed >= IDLE_MS) return 'idle';
  return 'active';
}

export function deriveCwdFromPath(filePath: string | null): string {
  if (!filePath) return '';
  const dir = filePath.replace(/\/[^/]+\.jsonl$/, '');
  const leaf = dir.split('/').pop() ?? '';
  if (!leaf.startsWith('-')) return dir;
  return '/' + leaf.slice(1).replace(/-/g, '/');
}

export function extractClaudeSessions(): AgentSession[] {
  const db = getDb();

  const aggregates = db
    .query<AggregateRow, []>(
      `SELECT m.session_id                       AS session_id,
              MAX(m.project)                     AS project,
              COUNT(*)                           AS message_count,
              MIN(CAST(m.ts AS INTEGER))         AS started_ms,
              MAX(CAST(m.ts AS INTEGER))         AS last_ms,
              s.summary                          AS summary,
              (SELECT path FROM indexed_files f
               WHERE f.session_id = m.session_id
               ORDER BY f.last_indexed_at DESC LIMIT 1) AS cwd,
              COALESCE(t.input_tokens, 0)          AS input_tokens,
              COALESCE(t.output_tokens, 0)         AS output_tokens,
              COALESCE(t.cache_creation_tokens, 0) AS cache_creation_tokens,
              COALESCE(t.cache_read_tokens, 0)     AS cache_read_tokens
       FROM session_messages m
       LEFT JOIN session_summaries s ON s.session_id = m.session_id
       LEFT JOIN (
         SELECT session_id,
                SUM(input_tokens)          AS input_tokens,
                SUM(output_tokens)         AS output_tokens,
                SUM(cache_creation_tokens) AS cache_creation_tokens,
                SUM(cache_read_tokens)     AS cache_read_tokens
         FROM message_tokens
         GROUP BY session_id
       ) t ON t.session_id = m.session_id
       GROUP BY m.session_id`
    )
    .all();

  // Latest real model per session. SQLite's MIN/MAX bare-column rule: the
  // non-aggregated `model` is taken from the same row that yields MAX(ts), i.e.
  // the most recent message. '<synthetic>' rows (no real API call) are excluded.
  const modelBySession = new Map<string, string | null>();
  const modelRows = db
    .query<ModelRow, []>(
      `SELECT session_id AS session_id, model AS model, MAX(ts) AS max_ts
       FROM message_tokens
       WHERE model IS NOT NULL AND model != '<synthetic>'
       GROUP BY session_id`
    )
    .all();
  for (const r of modelRows) modelBySession.set(r.session_id, r.model);

  const firstPrompts = new Map<string, string>();
  const firstPromptRows = db
    .query<FirstPromptRow, []>(
      `SELECT m.session_id AS session_id, m.content AS content
       FROM session_messages m
       JOIN (
         SELECT session_id, MIN(CAST(ts AS INTEGER)) AS min_ts
         FROM session_messages
         WHERE role = 'user'
         GROUP BY session_id
       ) f ON f.session_id = m.session_id
          AND CAST(m.ts AS INTEGER) = f.min_ts
       WHERE m.role = 'user'`
    )
    .all();
  for (const row of firstPromptRows) {
    if (!firstPrompts.has(row.session_id)) firstPrompts.set(row.session_id, row.content);
  }

  return aggregates.map((row) => {
    const startedAt = new Date(row.started_ms).toISOString();
    const lastActivityAt = new Date(row.last_ms).toISOString();
    const status = deriveStatus(row.last_ms);
    const cwd = deriveCwdFromPath(row.cwd);
    return {
      id: row.session_id,
      shortId: row.session_id.slice(0, 8).toLowerCase(),
      source: 'claude',
      cwd,
      projectName: row.project ?? 'unknown',
      branch: null,
      status,
      startedAt,
      lastActivityAt,
      endedAt: status === 'abandoned' ? lastActivityAt : null,
      messageCount: row.message_count,
      toolCalls: 0,
      agentsSpawned: 0,
      title: null,
      summary: row.summary,
      firstPrompt: firstPrompts.get(row.session_id) ?? null,
      model: modelBySession.get(row.session_id) ?? null,
      inputTokens: row.input_tokens,
      outputTokens: row.output_tokens,
      cacheCreationTokens: row.cache_creation_tokens,
      cacheReadTokens: row.cache_read_tokens,
      totalTokens:
        row.input_tokens + row.output_tokens + row.cache_creation_tokens + row.cache_read_tokens,
      tags: [],
      notes: null,
    };
  });
}
