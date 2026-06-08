import { existsSync } from 'node:fs';
import { Database } from 'bun:sqlite';
import type { AgentSession, SessionStatus } from '../types.js';
import { CURSOR_DB_PATH } from '../paths.js';

interface ComposerData {
  composerId: string;
  name?: string;
  status?: string;
  createdAt?: number;
  lastUpdatedAt?: number;
  modelConfig?: { modelName?: string };
  unifiedMode?: string;
  fullConversationHeadersOnly?: Array<unknown>;
}

function mapCursorStatus(cursorStatus: string | undefined): SessionStatus {
  switch (cursorStatus) {
    case 'completed':
    case 'done':
      return 'completed';
    case 'streaming':
    case 'active':
      return 'active';
    default:
      return 'idle';
  }
}

function composerToSession(data: ComposerData): AgentSession {
  const startedAt = data.createdAt ? new Date(data.createdAt).toISOString() : new Date().toISOString();
  const lastActivityAt = data.lastUpdatedAt ? new Date(data.lastUpdatedAt).toISOString() : startedAt;

  return {
    id: data.composerId,
    shortId: data.composerId.slice(0, 8).toLowerCase(),
    source: 'cursor',
    cwd: '',
    projectName: 'Cursor',
    branch: null,
    status: mapCursorStatus(data.status),
    startedAt,
    lastActivityAt,
    endedAt: data.status === 'completed' || data.status === 'done' ? lastActivityAt : null,
    messageCount: data.fullConversationHeadersOnly?.length ?? 0,
    toolCalls: 0,
    agentsSpawned: 0,
    title: data.name || null,
    summary: null,
    firstPrompt: null,
    model: data.modelConfig?.modelName ?? null,
    inputTokens: 0,
    outputTokens: 0,
    cacheCreationTokens: 0,
    cacheReadTokens: 0,
    totalTokens: 0,
    tags: [],
    notes: null,
  };
}

export function extractCursorSessions(): AgentSession[] {
  if (!existsSync(CURSOR_DB_PATH)) return [];

  try {
    const db = new Database(CURSOR_DB_PATH, { readonly: true });
    try {
      const rows = db
        .query<{ key: string; value: string }, []>(
          "SELECT key, value FROM cursorDiskKV WHERE key LIKE 'composerData:%'"
        )
        .all();

      return rows.reduce<AgentSession[]>((sessions, row) => {
        try {
          const data: ComposerData = JSON.parse(row.value);
          if (data.composerId) {
            sessions.push(composerToSession(data));
          }
        } catch {}
        return sessions;
      }, []);
    } finally {
      db.close();
    }
  } catch {
    return [];
  }
}
