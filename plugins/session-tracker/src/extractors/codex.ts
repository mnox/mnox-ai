import { existsSync, readdirSync, readFileSync } from 'node:fs';
import { basename, join } from 'node:path';
import { CODEX_SESSION_INDEX_PATH, CODEX_SESSIONS_DIR } from '../paths.js';
import type { AgentSession, SessionStatus } from '../types.js';

const IDLE_MS = 30 * 60 * 1000;
const ABANDONED_MS = 2 * 60 * 60 * 1000;
const MAX_FIRST_PROMPT_CHARS = 8_000;

interface CodexIndexEntry {
  title: string | null;
  updatedAt: string | null;
}

interface CodexUsage {
  inputTokens: number;
  outputTokens: number;
  cacheReadTokens: number;
  totalTokens: number | null;
}

function deriveStatus(lastMs: number): SessionStatus {
  const elapsed = Date.now() - lastMs;
  if (elapsed >= ABANDONED_MS) return 'abandoned';
  if (elapsed >= IDLE_MS) return 'idle';
  return 'active';
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function asString(value: unknown): string | null {
  return typeof value === 'string' && value.length > 0 ? value : null;
}

function asNumber(value: unknown): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : 0;
}

function parseJson(line: string): Record<string, unknown> | null {
  try {
    return asRecord(JSON.parse(line));
  } catch {
    return null;
  }
}

function readJsonl(path: string): Record<string, unknown>[] {
  try {
    return readFileSync(path, 'utf8')
      .split(/\r?\n/)
      .filter((line) => line.trim().length > 0)
      .map(parseJson)
      .filter((row): row is Record<string, unknown> => row !== null);
  } catch {
    return [];
  }
}

function walkJsonlFiles(root: string): string[] {
  if (!existsSync(root)) return [];
  const files: string[] = [];
  const visit = (dir: string) => {
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
      const path = join(dir, entry.name);
      if (entry.isDirectory()) {
        visit(path);
      } else if (entry.isFile() && entry.name.endsWith('.jsonl')) {
        files.push(path);
      }
    }
  };
  try {
    visit(root);
  } catch {
    return [];
  }
  return files.sort();
}

function loadIndex(): Map<string, CodexIndexEntry> {
  const entries = new Map<string, CodexIndexEntry>();
  if (!existsSync(CODEX_SESSION_INDEX_PATH)) return entries;

  for (const row of readJsonl(CODEX_SESSION_INDEX_PATH)) {
    const id = asString(row['id']);
    if (!id) continue;
    entries.set(id, {
      title: asString(row['thread_name']),
      updatedAt: asString(row['updated_at']),
    });
  }

  return entries;
}

function contentToText(content: unknown): string {
  if (typeof content === 'string') return content;
  if (!Array.isArray(content)) return '';

  return content
    .map((part) => {
      if (typeof part === 'string') return part;
      const record = asRecord(part);
      if (!record) return '';
      return asString(record['text']) ?? asString(record['content']) ?? '';
    })
    .filter((text) => text.length > 0)
    .join('\n');
}

function usageFromPayload(payload: Record<string, unknown>): CodexUsage | null {
  if (payload['type'] !== 'token_count') return null;
  const info = asRecord(payload['info']);
  const usage = asRecord(info?.['total_token_usage']);
  if (!usage) return null;

  const outputTokens = asNumber(usage['output_tokens']) + asNumber(usage['reasoning_output_tokens']);

  return {
    inputTokens: asNumber(usage['input_tokens']),
    outputTokens,
    cacheReadTokens: asNumber(usage['cached_input_tokens']),
    totalTokens: typeof usage['total_tokens'] === 'number' ? usage['total_tokens'] : null,
  };
}

function projectNameFrom(cwd: string, title: string | null): string {
  if (cwd) return basename(cwd) || cwd;
  return title ?? 'Codex';
}

function fallbackIdFromPath(path: string): string | null {
  return basename(path).match(/[0-9a-f]{8}-[0-9a-f-]{27,}/i)?.[0] ?? null;
}

function parseSessionFile(path: string, index: Map<string, CodexIndexEntry>): AgentSession | null {
  let id: string | null = null;
  let cwd = '';
  let provider: string | null = null;
  let model: string | null = null;
  let startedMs = Number.POSITIVE_INFINITY;
  let lastMs = 0;
  let messageCount = 0;
  let toolCalls = 0;
  let firstPrompt: string | null = null;
  let usage: CodexUsage = {
    inputTokens: 0,
    outputTokens: 0,
    cacheReadTokens: 0,
    totalTokens: null,
  };

  for (const row of readJsonl(path)) {
    const ts = Date.parse(asString(row['timestamp']) ?? '');
    if (!Number.isNaN(ts)) {
      startedMs = Math.min(startedMs, ts);
      lastMs = Math.max(lastMs, ts);
    }

    const payload = asRecord(row['payload']);
    if (!payload) continue;

    if (row['type'] === 'session_meta') {
      id = asString(payload['id']) ?? id;
      cwd = asString(payload['cwd']) ?? cwd;
      provider = asString(payload['model_provider']) ?? provider;
      model = asString(payload['model']) ?? model;
      continue;
    }

    if (row['type'] === 'response_item') {
      const itemType = asString(payload['type']);
      const role = asString(payload['role']);
      if (itemType === 'message' && (role === 'user' || role === 'assistant')) {
        messageCount += 1;
        if (role === 'user' && !firstPrompt) {
          const text = contentToText(payload['content']);
          firstPrompt = text.slice(0, MAX_FIRST_PROMPT_CHARS) || null;
        }
      }
      if (itemType === 'function_call' || itemType === 'tool_call') {
        toolCalls += 1;
      }
      model = asString(payload['model']) ?? model;
      continue;
    }

    if (row['type'] === 'event_msg') {
      const tokenUsage = usageFromPayload(payload);
      if (tokenUsage) usage = tokenUsage;
      model = asString(payload['model']) ?? model;
    }
  }

  id = id ?? fallbackIdFromPath(path);
  if (!id || !Number.isFinite(startedMs) || lastMs <= 0) return null;

  const indexEntry = index.get(id);
  const indexUpdatedMs = Date.parse(indexEntry?.updatedAt ?? '');
  if (!Number.isNaN(indexUpdatedMs)) {
    lastMs = Math.max(lastMs, indexUpdatedMs);
  }

  const startedAt = new Date(startedMs).toISOString();
  const lastActivityAt = new Date(lastMs).toISOString();
  const status = deriveStatus(lastMs);
  const totalTokens =
    usage.totalTokens ?? usage.inputTokens + usage.outputTokens + usage.cacheReadTokens;

  return {
    id,
    shortId: id.slice(0, 8).toLowerCase(),
    source: 'codex',
    cwd,
    projectName: projectNameFrom(cwd, indexEntry?.title ?? null),
    branch: null,
    status,
    startedAt,
    lastActivityAt,
    endedAt: status === 'abandoned' ? lastActivityAt : null,
    messageCount,
    toolCalls,
    agentsSpawned: 0,
    title: indexEntry?.title ?? null,
    summary: null,
    firstPrompt,
    model: model ?? provider,
    inputTokens: usage.inputTokens,
    outputTokens: usage.outputTokens,
    cacheCreationTokens: 0,
    cacheReadTokens: usage.cacheReadTokens,
    totalTokens,
    tags: [],
    notes: null,
  };
}

export function extractCodexSessions(): AgentSession[] {
  const index = loadIndex();
  return walkJsonlFiles(CODEX_SESSIONS_DIR).reduce<AgentSession[]>((sessions, file) => {
    const session = parseSessionFile(file, index);
    if (session) sessions.push(session);
    return sessions;
  }, []);
}
