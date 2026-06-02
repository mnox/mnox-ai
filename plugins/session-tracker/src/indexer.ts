import { readdirSync, statSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import { homedir } from 'node:os';
import { getDb, getIndexedFile, upsertIndexedFile, packF32, recordMessageTokens } from './db.js';
import { parseJsonl, type ParsedMessage } from './jsonl-parser.js';
import { chunkMessages } from './chunker.js';
import { embed, summarize, summarizeRationales, EMBED_MODEL_CHUNKS, EMBED_MODEL_SUMMARIES, SUMMARY_MODEL } from './openai-client.js';
import { embeddingsActive } from './config.js';
import { resolveSessionContext, recordToolEvents, listChangeSetsNeedingRationale, backfillRationale } from './change-tracker.js';
import { deriveCwdFromPath } from './extractors/claude.js';

const PROJECTS_DIR = join(homedir(), '.claude', 'projects');
const SUMMARY_DEBOUNCE_MS = 10 * 60 * 1000;
const SUMMARY_DEBOUNCE_MESSAGES = 5;
const MAX_SUMMARY_INPUT_CHARS = 24000;

export interface IndexResult {
  filesScanned: number;
  filesUpdated: number;
  messagesIndexed: number;
  chunksAdded: number;
  chunksEmbedded: number;
  summariesGenerated: number;
  tokenRowsRecorded: number;
}

function emptyResult(): IndexResult {
  return {
    filesScanned: 0,
    filesUpdated: 0,
    messagesIndexed: 0,
    chunksAdded: 0,
    chunksEmbedded: 0,
    summariesGenerated: 0,
    tokenRowsRecorded: 0,
  };
}

function walkJsonl(dir: string): string[] {
  const out: string[] = [];
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    const p = join(dir, e.name);
    if (e.isDirectory()) out.push(...walkJsonl(p));
    else if (e.isFile() && e.name.endsWith('.jsonl')) out.push(p);
  }
  return out;
}

export async function indexAll(): Promise<IndexResult> {
  const result = emptyResult();
  if (!existsSync(PROJECTS_DIR)) return result;

  const projectDirs = readdirSync(PROJECTS_DIR, { withFileTypes: true })
    .filter((d) => d.isDirectory())
    .map((d) => join(PROJECTS_DIR, d.name));

  for (const projectDir of projectDirs) {
    for (const path of walkJsonl(projectDir)) {
      try {
        const r = await indexFile(path);
        result.filesScanned++;
        if (r) {
          result.filesUpdated += r.filesUpdated;
          result.messagesIndexed += r.messagesIndexed;
          result.chunksAdded += r.chunksAdded;
          result.chunksEmbedded += r.chunksEmbedded;
          result.summariesGenerated += r.summariesGenerated;
          result.tokenRowsRecorded += r.tokenRowsRecorded;
        }
      } catch (err) {
        console.error(`[indexer] failed on ${path}:`, err);
      }
    }
  }

  return result;
}

export async function indexSession(sessionId: string): Promise<IndexResult> {
  const result = emptyResult();
  if (!existsSync(PROJECTS_DIR)) return result;
  const projectDirs = readdirSync(PROJECTS_DIR, { withFileTypes: true })
    .filter((d) => d.isDirectory())
    .map((d) => join(PROJECTS_DIR, d.name));
  const sidechain = sessionId.match(/^([0-9a-f-]+):agent-([0-9a-f]+)$/i);
  for (const projectDir of projectDirs) {
    const path = sidechain
      ? join(projectDir, sidechain[1]!, 'subagents', `agent-${sidechain[2]!}.jsonl`)
      : join(projectDir, `${sessionId}.jsonl`);
    if (existsSync(path)) {
      const r = await indexFile(path);
      if (r) return r;
    }
  }
  return result;
}

async function indexFile(path: string): Promise<IndexResult | null> {
  const db = getDb();
  const stat = statSync(path);
  const existing = getIndexedFile(db, path);
  if (existing && existing.mtime === stat.mtimeMs && existing.bytes_indexed === stat.size) {
    return null;
  }

  const fromByte = existing?.bytes_indexed ?? 0;
  const parsed = parseJsonl(path, fromByte);
  if (!parsed.sessionId) return null;

  const result = emptyResult();
  const sessionId = parsed.sessionId;
  const project = parsed.project;

  if (parsed.messages.length > 0) {
    // A full re-parse (byte cursor reset to 0 by backfill / schema change / manual
    // re-index) re-emits every message. session_messages is an FTS5 virtual table
    // (no UNIQUE constraint) and the chunker's overlap windows shift between an
    // incremental and a full parse, so per-row dedup keys can't catch the
    // duplicates. Instead we replace the session's prior derived rows. On a genuine
    // first index `fromByte` is also 0 but there are no prior rows, so the purge is
    // a no-op. change_sets/file_changes dedup via their own UNIQUE indexes and carry
    // LLM-generated rationale, so they are deliberately left untouched.
    const replaceSession = fromByte === 0;
    insertMessagesAndChunks(db, sessionId, project, parsed.messages, replaceSession, (added) => {
      result.chunksAdded += added;
    });
    result.messagesIndexed = parsed.messages.length;
  }

  // Change-tracking integration point: consume parsed.toolEvents from the same byte range.
  if (parsed.toolEvents.length > 0) {
    const cwd = deriveCwdFromPath(path);
    const ctx = resolveSessionContext({ sessionId, cwd: cwd || null, events: parsed.toolEvents });
    recordToolEvents({
      sessionId,
      project,
      events: parsed.toolEvents,
      cwd: ctx.worktree_path ?? ctx.repo_root ?? (cwd || null),
    });
  }

  // Token usage: idempotent on (session_id, message_id), so no replaceSession
  // special-casing is needed — replaying rows from a full re-parse just overwrites.
  if (parsed.usages.length > 0) {
    recordMessageTokens(db, sessionId, project, parsed.usages);
    result.tokenRowsRecorded = parsed.usages.length;
  }

  upsertIndexedFile(db, {
    path,
    session_id: sessionId,
    project,
    mtime: stat.mtimeMs,
    bytes_indexed: parsed.bytesRead,
    last_message_uuid: parsed.lastMessageUuid ?? existing?.last_message_uuid ?? null,
    last_indexed_at: Date.now(),
  });
  result.filesUpdated = 1;

  // Semantic features are opt-in and OFF by default. When inactive we skip ALL
  // embedding/summary generation entirely — no DB churn, no network calls. The
  // lexical FTS index (session_messages / chunks) is already populated above.
  if (embeddingsActive()) {
    result.chunksEmbedded = await embedPendingChunks(sessionId);
    if (await maybeGenerateSummary(sessionId, project)) {
      result.summariesGenerated = 1;
    }
  }

  return result;
}

function insertMessagesAndChunks(
  db: ReturnType<typeof getDb>,
  sessionId: string,
  project: string | null,
  messages: ParsedMessage[],
  replaceSession: boolean,
  onChunks: (added: number) => void
): void {
  const insertMsg = db.prepare(
    'INSERT INTO session_messages (session_id, project, role, ts, message_uuid, content) VALUES (?, ?, ?, ?, ?, ?)'
  );
  const insertChunk = db.prepare(
    'INSERT INTO chunks (session_id, project, ts_start, ts_end, first_message_uuid, last_message_uuid, text, token_count) VALUES (?, ?, ?, ?, ?, ?, ?, ?)'
  );
  // Purge this session's prior derived rows before re-inserting (full re-parse).
  // embeddings are deleted explicitly rather than relying on the ON DELETE CASCADE
  // so the purge is correct regardless of the foreign_keys pragma state.
  const purgeEmbeddings = db.prepare(
    'DELETE FROM embeddings WHERE chunk_id IN (SELECT id FROM chunks WHERE session_id = ?)'
  );
  const purgeChunks = db.prepare('DELETE FROM chunks WHERE session_id = ?');
  const purgeMessages = db.prepare('DELETE FROM session_messages WHERE session_id = ?');

  const tx = db.transaction(() => {
    if (replaceSession) {
      purgeEmbeddings.run(sessionId);
      purgeChunks.run(sessionId);
      purgeMessages.run(sessionId);
    }
    for (const m of messages) {
      insertMsg.run(sessionId, project, m.role, m.ts, m.uuid, m.text);
    }
    const chunks = chunkMessages(messages);
    for (const c of chunks) {
      insertChunk.run(
        sessionId,
        project,
        c.ts_start,
        c.ts_end,
        c.first_message_uuid,
        c.last_message_uuid,
        c.text,
        c.token_count
      );
    }
    onChunks(chunks.length);
  });
  tx();
}

/**
 * Populate message_tokens for ALL historical transcripts. Independent of the
 * byte cursor: re-parses each file from offset 0 and writes usage rows via the
 * idempotent INSERT OR REPLACE, so it's safe to run repeatedly and never
 * double-counts. Skips the chunk/embedding/summary pipeline entirely, so no
 * OpenAI key and no network — pure local walk.
 */
export function backfillTokens(): { files: number; rows: number; sessions: number } {
  const db = getDb();
  if (!existsSync(PROJECTS_DIR)) return { files: 0, rows: 0, sessions: 0 };

  const projectDirs = readdirSync(PROJECTS_DIR, { withFileTypes: true })
    .filter((d) => d.isDirectory())
    .map((d) => join(PROJECTS_DIR, d.name));

  let files = 0;
  let rows = 0;
  const sessions = new Set<string>();
  for (const projectDir of projectDirs) {
    for (const path of walkJsonl(projectDir)) {
      try {
        const parsed = parseJsonl(path, 0);
        if (!parsed.sessionId || parsed.usages.length === 0) continue;
        recordMessageTokens(db, parsed.sessionId, parsed.project, parsed.usages);
        files++;
        rows += parsed.usages.length;
        sessions.add(parsed.sessionId);
      } catch (err) {
        console.error(`[backfill-tokens] failed on ${path}:`, err);
      }
    }
  }
  return { files, rows, sessions: sessions.size };
}

export async function backfillEmbeddings(): Promise<{ embedded: number; sessions: number }> {
  if (!embeddingsActive()) return { embedded: 0, sessions: 0 };
  const db = getDb();
  const sessions = db
    .query(
      `SELECT DISTINCT c.session_id FROM chunks c
       LEFT JOIN embeddings e ON e.chunk_id = c.id
       WHERE e.chunk_id IS NULL`
    )
    .all() as Array<{ session_id: string }>;
  let embedded = 0;
  for (const s of sessions) {
    embedded += await embedPendingChunks(s.session_id);
  }
  return { embedded, sessions: sessions.length };
}

export async function backfillSummaries(): Promise<{ generated: number; sessions: number }> {
  if (!embeddingsActive()) return { generated: 0, sessions: 0 };
  const db = getDb();
  const sessions = db
    .query(
      `SELECT DISTINCT m.session_id, m.project FROM session_messages m
       LEFT JOIN session_summaries s ON s.session_id = m.session_id
       WHERE s.session_id IS NULL`
    )
    .all() as Array<{ session_id: string; project: string | null }>;
  let generated = 0;
  for (const s of sessions) {
    if (await maybeGenerateSummary(s.session_id, s.project)) generated++;
  }
  return { generated, sessions: sessions.length };
}

async function embedPendingChunks(sessionId: string): Promise<number> {
  const db = getDb();
  const rows = db
    .query(
      `SELECT c.id, c.text FROM chunks c
       LEFT JOIN embeddings e ON e.chunk_id = c.id
       WHERE c.session_id = ? AND e.chunk_id IS NULL
       ORDER BY c.id ASC`
    )
    .all(sessionId) as Array<{ id: number; text: string }>;
  if (rows.length === 0) return 0;

  const BATCH = 64;
  let embedded = 0;
  const insertEmbedding = db.prepare('INSERT INTO embeddings (chunk_id, model, vec) VALUES (?, ?, ?)');

  for (let i = 0; i < rows.length; i += BATCH) {
    const batch = rows.slice(i, i + BATCH);
    const inputs = batch.map((r) => r.text);
    const result = await embed(EMBED_MODEL_CHUNKS, inputs);
    if (!result) break;
    const tx = db.transaction(() => {
      for (const r of result) {
        const row = batch[r.index];
        if (!row) continue;
        insertEmbedding.run(row.id, EMBED_MODEL_CHUNKS, packF32(r.embedding));
        embedded++;
      }
    });
    tx();
  }
  return embedded;
}

async function maybeGenerateSummary(sessionId: string, project: string | null): Promise<boolean> {
  const db = getDb();
  const messageCount = (
    db.query('SELECT COUNT(*) AS n FROM session_messages WHERE session_id = ?').get(sessionId) as { n: number }
  ).n;
  if (messageCount === 0) return false;

  const existing = db
    .query('SELECT message_count_at_gen, generated_at FROM session_summaries WHERE session_id = ?')
    .get(sessionId) as { message_count_at_gen: number; generated_at: number } | null;

  const now = Date.now();
  if (existing) {
    const newMessages = messageCount - existing.message_count_at_gen;
    const ageMs = now - existing.generated_at;
    if (newMessages < SUMMARY_DEBOUNCE_MESSAGES && ageMs < SUMMARY_DEBOUNCE_MS) return false;
  }

  const transcript = (
    db
      .query(
        `SELECT role, content FROM session_messages WHERE session_id = ? ORDER BY ts ASC`
      )
      .all(sessionId) as Array<{ role: string; content: string }>
  )
    .map((r) => `[${r.role}] ${r.content}`)
    .join('\n\n');

  const truncated =
    transcript.length > MAX_SUMMARY_INPUT_CHARS
      ? transcript.slice(0, MAX_SUMMARY_INPUT_CHARS / 2) +
        '\n…\n' +
        transcript.slice(-MAX_SUMMARY_INPUT_CHARS / 2)
      : transcript;

  const summary = await summarize(truncated);
  if (!summary) return false;

  const embeddingResult = await embed(EMBED_MODEL_SUMMARIES, [summary]);
  const vec = embeddingResult?.[0]?.embedding ? packF32(embeddingResult[0].embedding) : null;

  db.query(
    `INSERT INTO session_summaries (session_id, project, summary, message_count_at_gen, generated_at, model, vec)
     VALUES (?, ?, ?, ?, ?, ?, ?)
     ON CONFLICT(session_id) DO UPDATE SET
       summary = excluded.summary,
       message_count_at_gen = excluded.message_count_at_gen,
       generated_at = excluded.generated_at,
       model = excluded.model,
       vec = excluded.vec,
       project = excluded.project`
  ).run(sessionId, project, summary, messageCount, now, SUMMARY_MODEL, vec);

  // Rationale backfill: runs in the same debounced pass, never breaks summary generation.
  await backfillChangeSetRationales(sessionId);

  return true;
}

/**
 * Backfill `change_sets.rationale` for rows where it is NULL.
 * Batches eligible rows into ONE LLM call, budget-capped by MAX_SUMMARY_INPUT_CHARS.
 * On any LLM failure the rationale stays NULL and retries on the next eligible pass.
 * Never throws; never overwrites a non-null rationale.
 */
async function backfillChangeSetRationales(sessionId: string): Promise<void> {
  try {
    const rows = listChangeSetsNeedingRationale(sessionId);
    if (rows.length === 0) return;

    // Accumulate rows into the budget — each row's contribution is its prompt + reasoning text.
    const batch: Array<{ id: number; triggerUserPrompt: string | null; reasoningExcerpt: string | null }> = [];
    let charCount = 0;
    for (const row of rows) {
      const contribution = (row.trigger_user_prompt?.length ?? 0) + (row.reasoning_excerpt?.length ?? 0);
      if (charCount + contribution > MAX_SUMMARY_INPUT_CHARS && batch.length > 0) break;
      batch.push({ id: row.id, triggerUserPrompt: row.trigger_user_prompt, reasoningExcerpt: row.reasoning_excerpt });
      charCount += contribution;
    }

    const rationales = await summarizeRationales(batch);
    if (!rationales) return; // LLM unavailable — leave NULL, retry next pass.

    const db = getDb();
    const tx = db.transaction(() => {
      for (let i = 0; i < batch.length; i++) {
        const item = batch[i];
        const rationale = rationales[i];
        if (item && rationale && rationale.length > 0) {
          backfillRationale(item.id, rationale);
        }
      }
    });
    tx();
  } catch (err) {
    // Never break summary generation — swallow and log.
    console.error('[indexer] backfillChangeSetRationales error:', err);
  }
}
