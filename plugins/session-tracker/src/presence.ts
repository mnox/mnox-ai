import { getDb } from './db.js';

export interface PresenceRow {
  session_id: string;
  tty: string | null;
  pid: number | null;
  cwd: string | null;
  status: 'live' | 'ended' | 'unknown';
  started_at: number;
  last_seen_at: number;
  ended_at: number | null;
  label: string | null;
}

export function recordStart(args: {
  session_id: string;
  tty: string | null;
  pid: number | null;
  cwd: string | null;
}): void {
  const db = getDb();
  const now = Date.now();
  db.query(
    `INSERT INTO session_ttys (session_id, tty, pid, cwd, status, started_at, last_seen_at)
     VALUES (?, ?, ?, ?, 'live', ?, ?)
     ON CONFLICT(session_id) DO UPDATE SET
       tty = COALESCE(excluded.tty, session_ttys.tty),
       pid = COALESCE(excluded.pid, session_ttys.pid),
       cwd = COALESCE(excluded.cwd, session_ttys.cwd),
       status = 'live',
       last_seen_at = excluded.last_seen_at,
       ended_at = NULL`
  ).run(args.session_id, args.tty, args.pid, args.cwd, now, now);
}

export function heartbeat(session_id: string, tty?: string | null): void {
  const db = getDb();
  const now = Date.now();
  if (tty) {
    db.query(
      `UPDATE session_ttys SET last_seen_at = ?, status = 'live', tty = ? WHERE session_id = ?`
    ).run(now, tty, session_id);
    if ((db.query('SELECT changes() AS n').get() as { n: number }).n === 0) {
      db.query(
        `INSERT INTO session_ttys (session_id, tty, status, started_at, last_seen_at) VALUES (?, ?, 'live', ?, ?)`
      ).run(session_id, tty, now, now);
    }
  } else {
    db.query(`UPDATE session_ttys SET last_seen_at = ?, status = 'live' WHERE session_id = ?`).run(
      now,
      session_id
    );
  }
}

export function recordEnd(session_id: string): void {
  const db = getDb();
  const now = Date.now();
  db.query(
    `UPDATE session_ttys SET status = 'ended', ended_at = ?, last_seen_at = ? WHERE session_id = ?`
  ).run(now, now, session_id);
}

export function getPresence(session_id_prefix: string): PresenceRow | null {
  const db = getDb();
  return (
    (db
      .query(`SELECT * FROM session_ttys WHERE session_id LIKE ? LIMIT 1`)
      .get(`${session_id_prefix}%`) as PresenceRow | null) ?? null
  );
}

/**
 * Persist a tab title label keyed by tty.
 *
 * The tty — not session_id — is the durable key for tab titles. A single claude
 * process keeps the same controlling tty across resume/compaction even as its
 * session_id churns (observed live: tty ttys012 held both an `ended` and a fresh
 * `live` session row under the same pid). Keying by tty means the label written
 * by set_session_label is the same label the stop-hook re-asserts every turn,
 * because both resolve the same physical tty.
 */
export function setTabLabel(tty: string, label: string): void {
  const db = getDb();
  db.query(
    `INSERT INTO tab_labels (tty, label, updated_at) VALUES (?, ?, ?)
     ON CONFLICT(tty) DO UPDATE SET label = excluded.label, updated_at = excluded.updated_at`
  ).run(tty, label, Date.now());
}

/** Look up the current tab title label for a tty (null if none set). */
export function getTabLabel(tty: string): string | null {
  const db = getDb();
  const row = db.query(`SELECT label FROM tab_labels WHERE tty = ? LIMIT 1`).get(tty) as
    | { label: string }
    | null;
  return row?.label ?? null;
}
