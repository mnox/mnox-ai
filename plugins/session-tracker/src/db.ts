import { Database } from 'bun:sqlite';
import { existsSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { homedir } from 'node:os';
import type { ParsedUsage } from './jsonl-parser.js';

export const SESSIONS_DIR = join(homedir(), '.claude', 'sessions');
// SESSION_TRACKER_DB_PATH overrides the default location — used to point at a
// throwaway copy when dry-running a backfill so the live index is never touched.
export const INDEX_DB_PATH = process.env['SESSION_TRACKER_DB_PATH'] || join(SESSIONS_DIR, 'index.db');

let _db: Database | null = null;

export function getDb(): Database {
  if (_db) return _db;
  if (!existsSync(dirname(INDEX_DB_PATH))) {
    mkdirSync(dirname(INDEX_DB_PATH), { recursive: true });
  }
  const db = new Database(INDEX_DB_PATH);
  db.exec('PRAGMA journal_mode = WAL');
  db.exec('PRAGMA synchronous = NORMAL');
  db.exec('PRAGMA foreign_keys = ON');
  initSchema(db);
  _db = db;
  return db;
}

function initSchema(db: Database): void {
  db.exec(`
    CREATE TABLE IF NOT EXISTS indexed_files (
      path TEXT PRIMARY KEY,
      session_id TEXT NOT NULL,
      project TEXT,
      mtime INTEGER NOT NULL,
      bytes_indexed INTEGER NOT NULL DEFAULT 0,
      last_message_uuid TEXT,
      last_indexed_at INTEGER NOT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_indexed_files_session ON indexed_files(session_id);

    CREATE VIRTUAL TABLE IF NOT EXISTS session_messages USING fts5(
      session_id UNINDEXED,
      project UNINDEXED,
      role UNINDEXED,
      ts UNINDEXED,
      message_uuid UNINDEXED,
      content,
      tokenize = 'porter unicode61'
    );

    CREATE TABLE IF NOT EXISTS chunks (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      session_id TEXT NOT NULL,
      project TEXT,
      ts_start INTEGER NOT NULL,
      ts_end INTEGER NOT NULL,
      first_message_uuid TEXT,
      last_message_uuid TEXT,
      text TEXT NOT NULL,
      token_count INTEGER NOT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_chunks_session ON chunks(session_id);

    CREATE TABLE IF NOT EXISTS embeddings (
      chunk_id INTEGER PRIMARY KEY REFERENCES chunks(id) ON DELETE CASCADE,
      model TEXT NOT NULL,
      vec BLOB NOT NULL
    );

    CREATE TABLE IF NOT EXISTS session_summaries (
      session_id TEXT PRIMARY KEY,
      project TEXT,
      summary TEXT NOT NULL,
      message_count_at_gen INTEGER NOT NULL,
      generated_at INTEGER NOT NULL,
      model TEXT NOT NULL,
      vec BLOB
    );

    CREATE TABLE IF NOT EXISTS session_ttys (
      session_id TEXT PRIMARY KEY,
      tty TEXT,
      pid INTEGER,
      cwd TEXT,
      status TEXT NOT NULL DEFAULT 'live',
      started_at INTEGER NOT NULL,
      last_seen_at INTEGER NOT NULL,
      ended_at INTEGER
    );

    CREATE INDEX IF NOT EXISTS idx_session_ttys_status ON session_ttys(status);

    -- Tab titles are keyed by tty, NOT session_id. A single claude process keeps
    -- its tty across resume/compaction even as its session_id churns, so the tty
    -- is the only key the label-writer (set_session_label tool) and the label-
    -- reader (stop-hook re-assert) can both observe and agree on across a churn.
    CREATE TABLE IF NOT EXISTS tab_labels (
      tty        TEXT PRIMARY KEY,
      label      TEXT NOT NULL,
      updated_at INTEGER NOT NULL
    );

    CREATE TABLE IF NOT EXISTS session_context (
      session_id     TEXT PRIMARY KEY,
      repo_root      TEXT,
      worktree_path  TEXT,
      branch         TEXT,
      branch_history TEXT,
      pr_number      INTEGER,
      pr_url         TEXT,
      shipyard_task  TEXT,
      field_state    TEXT,
      created_at     INTEGER NOT NULL,
      updated_at     INTEGER NOT NULL
    );

    CREATE TABLE IF NOT EXISTS change_sets (
      id                  INTEGER PRIMARY KEY AUTOINCREMENT,
      session_id          TEXT NOT NULL,
      project             TEXT,
      ts_start            INTEGER NOT NULL,
      ts_end              INTEGER NOT NULL,
      first_message_uuid  TEXT NOT NULL,
      last_message_uuid   TEXT,
      trigger_user_prompt TEXT,
      reasoning_excerpt   TEXT,
      rationale           TEXT,
      branch              TEXT,
      worktree_path       TEXT,
      pr_number           INTEGER,
      shipyard_task       TEXT,
      created_at          INTEGER NOT NULL
    );

    CREATE UNIQUE INDEX IF NOT EXISTS idx_change_sets_session_trigger
      ON change_sets(session_id, first_message_uuid);
    CREATE INDEX IF NOT EXISTS idx_change_sets_session ON change_sets(session_id);
    CREATE INDEX IF NOT EXISTS idx_change_sets_ts ON change_sets(ts_start);

    CREATE TABLE IF NOT EXISTS file_changes (
      id            INTEGER PRIMARY KEY AUTOINCREMENT,
      change_set_id INTEGER NOT NULL REFERENCES change_sets(id) ON DELETE CASCADE,
      session_id    TEXT NOT NULL,
      ts            INTEGER NOT NULL,
      tool_name     TEXT NOT NULL,
      file_path     TEXT,
      change_kind   TEXT NOT NULL,
      message_uuid  TEXT NOT NULL,
      tool_input    TEXT
    );

    CREATE UNIQUE INDEX IF NOT EXISTS idx_file_changes_dedup
      ON file_changes(message_uuid, tool_name, file_path);
    CREATE INDEX IF NOT EXISTS idx_file_changes_change_set ON file_changes(change_set_id);
    CREATE INDEX IF NOT EXISTS idx_file_changes_session ON file_changes(session_id);
    CREATE INDEX IF NOT EXISTS idx_file_changes_path ON file_changes(file_path);

    -- Per-assistant-message token usage. Keyed by (session_id, message_id) so
    -- writes are idempotent: streaming re-emits the same message_id with identical
    -- usage, and full re-parses replay every message — INSERT OR REPLACE collapses
    -- both to one row, sidestepping the incremental-cursor double-count trap. The
    -- four token buckets are kept separate (input / output / cache-write / cache-read)
    -- because they price differently; per-session and lifetime totals are SUM()s.
    CREATE TABLE IF NOT EXISTS message_tokens (
      session_id            TEXT NOT NULL,
      message_id            TEXT NOT NULL,
      project               TEXT,
      model                 TEXT,
      ts                    INTEGER NOT NULL,
      input_tokens          INTEGER NOT NULL DEFAULT 0,
      output_tokens         INTEGER NOT NULL DEFAULT 0,
      cache_creation_tokens INTEGER NOT NULL DEFAULT 0,
      cache_read_tokens     INTEGER NOT NULL DEFAULT 0,
      PRIMARY KEY (session_id, message_id)
    );

    CREATE INDEX IF NOT EXISTS idx_message_tokens_session ON message_tokens(session_id);
    CREATE INDEX IF NOT EXISTS idx_message_tokens_model ON message_tokens(model);
    CREATE INDEX IF NOT EXISTS idx_message_tokens_ts ON message_tokens(ts);
  `);

  // Idempotent migration: add label column if it does not exist yet.
  // ALTER TABLE fails with "duplicate column" on pre-existing tables, which is
  // the expected signal that the migration already ran — swallow it silently.
  try {
    db.exec(`ALTER TABLE session_ttys ADD COLUMN label TEXT`);
  } catch {
    // column already present — no-op
  }
}

export interface IndexedFileRow {
  path: string;
  session_id: string;
  project: string | null;
  mtime: number;
  bytes_indexed: number;
  last_message_uuid: string | null;
  last_indexed_at: number;
}

export function getIndexedFile(db: Database, path: string): IndexedFileRow | undefined {
  const row = db.query('SELECT * FROM indexed_files WHERE path = ?').get(path) as IndexedFileRow | null;
  return row ?? undefined;
}

export function upsertIndexedFile(db: Database, row: IndexedFileRow): void {
  db.query(
    `INSERT INTO indexed_files (path, session_id, project, mtime, bytes_indexed, last_message_uuid, last_indexed_at)
     VALUES (?, ?, ?, ?, ?, ?, ?)
     ON CONFLICT(path) DO UPDATE SET
       mtime = excluded.mtime,
       bytes_indexed = excluded.bytes_indexed,
       last_message_uuid = excluded.last_message_uuid,
       last_indexed_at = excluded.last_indexed_at`
  ).run(
    row.path,
    row.session_id,
    row.project,
    row.mtime,
    row.bytes_indexed,
    row.last_message_uuid,
    row.last_indexed_at
  );
}

/**
 * Persist per-message token usage. Idempotent: INSERT OR REPLACE on the
 * (session_id, message_id) primary key means replaying the same message —
 * whether from streaming-partial lines or a full re-parse — overwrites rather
 * than accumulates. Safe to call on every index pass.
 */
export function recordMessageTokens(
  db: Database,
  sessionId: string,
  project: string | null,
  usages: ParsedUsage[]
): void {
  if (usages.length === 0) return;
  const stmt = db.prepare(
    `INSERT OR REPLACE INTO message_tokens
       (session_id, message_id, project, model, ts,
        input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`
  );
  const tx = db.transaction(() => {
    for (const u of usages) {
      stmt.run(
        sessionId,
        u.messageId,
        project,
        u.model,
        u.ts,
        u.inputTokens,
        u.outputTokens,
        u.cacheCreationTokens,
        u.cacheReadTokens
      );
    }
  });
  tx();
}

export function packF32(values: number[]): Buffer {
  const buf = Buffer.allocUnsafe(values.length * 4);
  for (let i = 0; i < values.length; i++) buf.writeFloatLE(values[i]!, i * 4);
  return buf;
}

export function unpackF32(buf: Buffer | Uint8Array): Float32Array {
  const u8 = buf instanceof Uint8Array ? buf : new Uint8Array(buf);
  return new Float32Array(u8.buffer, u8.byteOffset, u8.byteLength / 4);
}

export function cosine(a: Float32Array, b: Float32Array): number {
  if (a.length !== b.length) return 0;
  let dot = 0;
  let na = 0;
  let nb = 0;
  for (let i = 0; i < a.length; i++) {
    const av = a[i]!;
    const bv = b[i]!;
    dot += av * bv;
    na += av * av;
    nb += bv * bv;
  }
  if (na === 0 || nb === 0) return 0;
  return dot / (Math.sqrt(na) * Math.sqrt(nb));
}
