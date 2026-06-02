import { spawnSync } from 'node:child_process';
import { getDb } from './db.js';
import type { ParsedToolEvent, ChangeKind } from './jsonl-parser.js';

// ---------------------------------------------------------------------------
// Row types (shared with WS5 server.ts)
// ---------------------------------------------------------------------------

export interface ChangeSetRow {
  id: number;
  session_id: string;
  project: string | null;
  ts_start: number;
  ts_end: number;
  first_message_uuid: string;
  last_message_uuid: string | null;
  trigger_user_prompt: string | null;
  reasoning_excerpt: string | null;
  rationale: string | null;
  branch: string | null;
  worktree_path: string | null;
  pr_number: number | null;
  shipyard_task: string | null;
  created_at: number;
}

export interface SessionContextRow {
  session_id: string;
  repo_root: string | null;
  worktree_path: string | null;
  branch: string | null;
  branch_history: string | null; // JSON array of {branch, ts}
  pr_number: number | null;
  pr_url: string | null;
  shipyard_task: string | null;
  field_state: string | null; // JSON per-field {resolved, source, ts}
  created_at: number;
  updated_at: number;
}

export interface FileChangeRow {
  id: number;
  change_set_id: number;
  session_id: string;
  ts: number;
  tool_name: string;
  file_path: string | null;
  change_kind: ChangeKind;
  message_uuid: string;
  tool_input: string | null; // JSON TEXT (minimal captured args)
}

export interface AgentChangesFilters {
  session_id?: string;
  since?: number;
  until?: number;
  file_path?: string;     // substring match on file_changes.file_path
  branch?: string;        // exact match on change_sets.branch
  pr?: number;            // change_sets.pr_number
  shipyard_task?: string; // change_sets.shipyard_task
  limit?: number;         // default 25, max 100
}

// ---------------------------------------------------------------------------
// Shell-out hygiene (contract §G4)
// ---------------------------------------------------------------------------

const GIT_TIMEOUT_MS = 3000;
const GH_TIMEOUT_MS = 5000;

/**
 * Result of a bounded shell-out, distinguishing a STRUCTURAL negative
 * (process ran to completion but the answer is empty/negative — e.g. not a git
 * repo, no open PR) from a TRANSIENT failure (timeout / SIGKILL / spawn error /
 * gh auth/network). The caller caches structural negatives as `unavailable`
 * (never re-attempted) and leaves transients `pending` (retried next pass).
 */
type SpawnOutcome =
  | { kind: 'ok'; value: string }
  | { kind: 'unavailable' } // clean non-zero/empty exit — structural negative
  | { kind: 'transient' }; // timeout / SIGKILL / spawn error

function safeSpawn(cmd: string, args: string[], cwd: string, timeout: number): SpawnOutcome {
  try {
    const r = spawnSync(cmd, args, { cwd, encoding: 'utf8', timeout, killSignal: 'SIGKILL' });
    // r.error set (e.g. ETIMEDOUT) OR status null (killed by signal) → transient.
    if (r.error || r.status === null) return { kind: 'transient' };
    if (typeof r.stdout !== 'string') return { kind: 'unavailable' };
    const out = r.stdout.trim();
    // Clean exit (status is a number, incl. non-zero like "not a git repo" /
    // "no PR found") with no usable stdout → structural negative.
    if (out.length === 0) return { kind: 'unavailable' };
    if (r.status !== 0) return { kind: 'unavailable' };
    return { kind: 'ok', value: out };
  } catch {
    return { kind: 'transient' };
  }
}

// ---------------------------------------------------------------------------
// Field-state helpers
// ---------------------------------------------------------------------------

type FieldSource = 'transcript' | 'git' | 'gh';

/**
 * 3-state resolution status per field:
 * - `resolved`    — value found; never re-attempt.
 * - `unavailable` — structural negative (cwd not a repo / no PR / not a worktree);
 *                   cached, never re-attempt. Bounds the recurring shell-out tax.
 * - `pending`     — transient failure (timeout / SIGKILL / gh net/auth); retry next pass.
 * A field with NO entry is implicitly `pending` (never attempted yet).
 */
type FieldStatus = 'resolved' | 'unavailable' | 'pending';

interface FieldMeta {
  status: FieldStatus;
  source: FieldSource;
  ts: number;
}

type FieldStateMap = Partial<Record<string, FieldMeta>>;

function parseFieldState(raw: string | null): FieldStateMap {
  if (!raw) return {};
  try {
    return JSON.parse(raw) as FieldStateMap;
  } catch {
    return {};
  }
}

/** Skip a field only when it is terminally settled (resolved or structurally unavailable). */
function isSettled(state: FieldStateMap, field: string): boolean {
  const s = state[field]?.status;
  return s === 'resolved' || s === 'unavailable';
}

function markResolved(state: FieldStateMap, field: string, source: FieldSource, now: number): void {
  state[field] = { status: 'resolved', source, ts: now };
}

function markUnavailable(state: FieldStateMap, field: string, source: FieldSource, now: number): void {
  state[field] = { status: 'unavailable', source, ts: now };
}

function markPending(state: FieldStateMap, field: string, source: FieldSource, now: number): void {
  state[field] = { status: 'pending', source, ts: now };
}

// ---------------------------------------------------------------------------
// Transcript scraping helpers
// ---------------------------------------------------------------------------

/** Extract a Shipyard task ID (e.g. "CX-160") from event prompts / tool names. */
function scrapeShipyardTask(events: ParsedToolEvent[]): string | null {
  const CX_PATTERN = /\b([A-Z]{2,6}-\d+)\b/;
  for (const ev of events) {
    if (ev.triggerUserPrompt) {
      const m = CX_PATTERN.exec(ev.triggerUserPrompt);
      if (m) return m[1]!;
    }
    if (ev.changeKind === 'shipyard') {
      const input = ev.toolInput as Record<string, unknown>;
      if (typeof input['task_id'] === 'string') return input['task_id'];
    }
  }
  return null;
}

/** Extract a branch name from git tool events. */
function scrapeBranchFromEvents(events: ParsedToolEvent[]): string | null {
  const BRANCH_CMDS = /\b(?:checkout|switch|branch)\s+(?:-[bcCBt]+\s+)?([^\s-][^\s]*)/;
  const ABBREV_RE = /\brev-parse\s+--abbrev-ref\s+HEAD\b/;
  for (const ev of events) {
    if (ev.changeKind === 'git' && ev.toolInput) {
      const cmd = (ev.toolInput as Record<string, unknown>)['command'];
      if (typeof cmd === 'string') {
        if (ABBREV_RE.test(cmd)) {
          // This just indicates git was queried, can't extract result from input
          continue;
        }
        const m = BRANCH_CMDS.exec(cmd);
        if (m && m[1] && !m[1].startsWith('-')) return m[1]!;
      }
    }
    if (ev.triggerUserPrompt) {
      const m = /\b(?:branch|checkout|switch)\s+(?:-[bcCBt]+\s+)?([a-zA-Z0-9][a-zA-Z0-9/_.-]{2,})\b/.exec(
        ev.triggerUserPrompt,
      );
      if (m && m[1]) return m[1]!;
    }
  }
  return null;
}

/** Extract PR number from gh tool events or prompt text. */
function scrapePrFromEvents(events: ParsedToolEvent[]): { prNumber: number; prUrl: string | null } | null {
  const PR_URL_RE = /https?:\/\/github\.com\/[^/]+\/[^/]+\/pull\/(\d+)/;
  const PR_NUMBER_RE = /\bPR\s*#?(\d+)\b|\bpull\s+request\s+#?(\d+)\b/i;
  for (const ev of events) {
    if (ev.changeKind === 'gh' && ev.toolInput) {
      const cmd = (ev.toolInput as Record<string, unknown>)['command'];
      if (typeof cmd === 'string') {
        const urlMatch = PR_URL_RE.exec(cmd);
        if (urlMatch) {
          return { prNumber: parseInt(urlMatch[1]!, 10), prUrl: urlMatch[0] };
        }
      }
    }
    const text = ev.triggerUserPrompt ?? '';
    const urlMatch = PR_URL_RE.exec(text);
    if (urlMatch) return { prNumber: parseInt(urlMatch[1]!, 10), prUrl: urlMatch[0] };
    const numMatch = PR_NUMBER_RE.exec(text);
    if (numMatch) {
      const n = numMatch[1] ?? numMatch[2];
      if (n) return { prNumber: parseInt(n, 10), prUrl: null };
    }
  }
  return null;
}

// ---------------------------------------------------------------------------
// Foundation resolver
// ---------------------------------------------------------------------------

export function resolveSessionContext(args: {
  sessionId: string;
  cwd: string | null;
  events: ParsedToolEvent[];
}): SessionContextRow {
  const { sessionId, cwd, events } = args;
  const db = getDb();
  const now = Date.now();

  // Load existing row or start fresh
  const existing = db.query<SessionContextRow, [string]>(
    'SELECT * FROM session_context WHERE session_id = ?',
  ).get(sessionId);

  const state = parseFieldState(existing?.field_state ?? null);

  let repoRoot = existing?.repo_root ?? null;
  let worktreePath = existing?.worktree_path ?? null;
  let branch = existing?.branch ?? null;
  let branchHistory: Array<{ branch: string; ts: number }> = [];
  try {
    branchHistory = JSON.parse(existing?.branch_history ?? '[]') as Array<{ branch: string; ts: number }>;
  } catch {
    branchHistory = [];
  }
  let prNumber = existing?.pr_number ?? null;
  let prUrl = existing?.pr_url ?? null;
  let shipyardTask = existing?.shipyard_task ?? null;

  // --- Step 1: transcript scrape (zero-cost) ---
  // A non-match here does NOT settle the field — it stays implicitly `pending`
  // so Step 2's bounded shell-out can attempt it.

  if (!isSettled(state, 'shipyard_task')) {
    const scraped = scrapeShipyardTask(events);
    if (scraped) {
      shipyardTask = scraped;
      markResolved(state, 'shipyard_task', 'transcript', now);
    }
  }

  if (!isSettled(state, 'branch')) {
    const scraped = scrapeBranchFromEvents(events);
    if (scraped) {
      branch = scraped;
      markResolved(state, 'branch', 'transcript', now);
    }
  }

  if (!isSettled(state, 'pr_number')) {
    const scraped = scrapePrFromEvents(events);
    if (scraped) {
      prNumber = scraped.prNumber;
      if (scraped.prUrl) prUrl = scraped.prUrl;
      markResolved(state, 'pr_number', 'transcript', now);
    }
  }

  // --- Step 2: shell-out for still-unsettled fields (gated by field_state).
  // Each shell-out is classified: ok → resolved; unavailable (clean negative,
  // e.g. not a repo / no PR) → cached, never retried; transient (timeout/error)
  // → left pending for retry next pass.

  const effectiveCwd = cwd && cwd.length > 0 ? cwd : null;

  if (effectiveCwd && !isSettled(state, 'repo_root')) {
    const r = safeSpawn('git', ['-C', effectiveCwd, 'rev-parse', '--show-toplevel'], effectiveCwd, GIT_TIMEOUT_MS);
    if (r.kind === 'ok') {
      repoRoot = r.value;
      markResolved(state, 'repo_root', 'git', now);
    } else if (r.kind === 'unavailable') {
      markUnavailable(state, 'repo_root', 'git', now);
    } else {
      markPending(state, 'repo_root', 'git', now);
    }
  }

  if (effectiveCwd && !isSettled(state, 'worktree_path')) {
    // Worktree path = the cwd itself (differs from repo_root only when in a worktree).
    // Resolvable from cwd alone (no shell-out) — always a structural value here.
    if (repoRoot) {
      worktreePath = effectiveCwd !== repoRoot ? effectiveCwd : repoRoot;
      markResolved(state, 'worktree_path', 'git', now);
    } else if (isSettled(state, 'repo_root')) {
      // repo_root is structurally unavailable → cwd is not a repo; no worktree.
      markUnavailable(state, 'worktree_path', 'git', now);
    }
    // else repo_root still pending (transient) → leave worktree_path pending too.
  }

  if (effectiveCwd && !isSettled(state, 'branch')) {
    const r = safeSpawn('git', ['-C', effectiveCwd, 'rev-parse', '--abbrev-ref', 'HEAD'], effectiveCwd, GIT_TIMEOUT_MS);
    if (r.kind === 'ok' && r.value !== 'HEAD') {
      branch = r.value;
      markResolved(state, 'branch', 'git', now);
    } else if (r.kind === 'transient') {
      markPending(state, 'branch', 'git', now);
    } else {
      // unavailable, or detached HEAD ('HEAD') → structural negative.
      markUnavailable(state, 'branch', 'git', now);
    }
  }

  if (effectiveCwd && !isSettled(state, 'pr_number')) {
    const r = safeSpawn('gh', ['pr', 'view', '--json', 'number,url'], effectiveCwd, GH_TIMEOUT_MS);
    if (r.kind === 'transient') {
      // timeout / auth / network → retry next pass.
      markPending(state, 'pr_number', 'gh', now);
    } else if (r.kind === 'unavailable') {
      // clean "no PR found" exit → structural negative; never retry.
      markUnavailable(state, 'pr_number', 'gh', now);
    } else {
      try {
        const parsed = JSON.parse(r.value) as Record<string, unknown>;
        if (typeof parsed['number'] === 'number') {
          prNumber = parsed['number'];
          if (typeof parsed['url'] === 'string') prUrl = parsed['url'];
          markResolved(state, 'pr_number', 'gh', now);
        } else {
          // well-formed JSON without a number → no PR; structural negative.
          markUnavailable(state, 'pr_number', 'gh', now);
        }
      } catch {
        // malformed JSON from a clean exit → treat as structural negative.
        markUnavailable(state, 'pr_number', 'gh', now);
      }
    }
  }

  // --- Append to branch_history if branch changed ---
  if (branch && (branchHistory.length === 0 || branchHistory[branchHistory.length - 1]?.branch !== branch)) {
    branchHistory.push({ branch, ts: now });
  }

  const row: SessionContextRow = {
    session_id: sessionId,
    repo_root: repoRoot,
    worktree_path: worktreePath,
    branch,
    branch_history: JSON.stringify(branchHistory),
    pr_number: prNumber,
    pr_url: prUrl,
    shipyard_task: shipyardTask,
    field_state: JSON.stringify(state),
    created_at: existing?.created_at ?? now,
    updated_at: now,
  };

  upsertSessionContext(row);
  return row;
}

// ---------------------------------------------------------------------------
// session_context upsert — COALESCE-style preserve-if-non-null on resolved fields
// ---------------------------------------------------------------------------

export function upsertSessionContext(row: Partial<SessionContextRow> & { session_id: string }): void {
  const db = getDb();
  const now = Date.now();
  // Never overwrite rationale (owned by §4) — rationale is not on session_context, but
  // apply the same preserve-non-null pattern to all fields WS4 might write.
  db.query(
    `INSERT INTO session_context
       (session_id, repo_root, worktree_path, branch, branch_history, pr_number, pr_url,
        shipyard_task, field_state, created_at, updated_at)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
     ON CONFLICT(session_id) DO UPDATE SET
       repo_root      = COALESCE(excluded.repo_root, session_context.repo_root),
       worktree_path  = COALESCE(excluded.worktree_path, session_context.worktree_path),
       branch         = COALESCE(excluded.branch, session_context.branch),
       branch_history = COALESCE(excluded.branch_history, session_context.branch_history),
       pr_number      = COALESCE(excluded.pr_number, session_context.pr_number),
       pr_url         = COALESCE(excluded.pr_url, session_context.pr_url),
       shipyard_task  = COALESCE(excluded.shipyard_task, session_context.shipyard_task),
       field_state    = COALESCE(excluded.field_state, session_context.field_state),
       updated_at     = excluded.updated_at`,
  ).run(
    row.session_id,
    row.repo_root ?? null,
    row.worktree_path ?? null,
    row.branch ?? null,
    row.branch_history ?? null,
    row.pr_number ?? null,
    row.pr_url ?? null,
    row.shipyard_task ?? null,
    row.field_state ?? null,
    row.created_at ?? now,
    row.updated_at ?? now,
  );
}

// ---------------------------------------------------------------------------
// Core ingestion: group events into change_sets + file_changes
// ---------------------------------------------------------------------------

export function recordToolEvents(args: {
  sessionId: string;
  project: string | null;
  events: ParsedToolEvent[];
  cwd: string | null;
}): { changeSetsCreated: number; fileChangesInserted: number } {
  const { sessionId, project, events } = args;
  const db = getDb();

  // Drop events with null triggerMessageUuid — cannot be grouped by turn boundary
  const eligible = events.filter((ev) => ev.triggerMessageUuid !== null);
  if (eligible.length === 0) return { changeSetsCreated: 0, fileChangesInserted: 0 };

  // Group by triggerMessageUuid
  const groups = new Map<string, ParsedToolEvent[]>();
  for (const ev of eligible) {
    const key = ev.triggerMessageUuid!;
    let group = groups.get(key);
    if (!group) {
      group = [];
      groups.set(key, group);
    }
    group.push(ev);
  }

  // Resolve foundation snapshot once for this batch
  const ctx = resolveSessionContext({ sessionId, cwd: args.cwd, events });

  let changeSetsCreated = 0;
  let fileChangesInserted = 0;
  const now = Date.now();

  const tx = db.transaction(() => {
    const selectExisting = db.prepare<{ id: number }, [string, string]>(
      'SELECT id FROM change_sets WHERE session_id = ? AND first_message_uuid = ?',
    );

    const upsertChangeSetNoReturn = db.prepare(
      `INSERT INTO change_sets
         (session_id, project, ts_start, ts_end, first_message_uuid, last_message_uuid,
          trigger_user_prompt, reasoning_excerpt, rationale, branch, worktree_path,
          pr_number, shipyard_task, created_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?)
       ON CONFLICT(session_id, first_message_uuid) DO UPDATE SET
         ts_end            = MAX(change_sets.ts_end, excluded.ts_end),
         last_message_uuid = excluded.last_message_uuid`,
    );

    const insertFileChange = db.prepare(
      `INSERT INTO file_changes
         (change_set_id, session_id, ts, tool_name, file_path, change_kind, message_uuid, tool_input)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?)
       ON CONFLICT(message_uuid, tool_name, file_path) DO NOTHING`,
    );

    for (const [triggerUuid, groupEvents] of groups) {
      const tsVals = groupEvents.map((e) => e.ts);
      const tsStart = Math.min(...tsVals);
      const tsEnd = Math.max(...tsVals);
      const lastEvent = groupEvents[groupEvents.length - 1]!;
      const firstEvent = groupEvents[0]!;

      // Pick representative trigger prompt + reasoning from first event in group
      const triggerUserPrompt = firstEvent.triggerUserPrompt;
      // Use reasoning from the event with the longest excerpt, or first non-null
      const reasoningExcerpt = groupEvents.reduce<string | null>((best, ev) => {
        if (!ev.reasoningExcerpt) return best;
        if (!best) return ev.reasoningExcerpt;
        return ev.reasoningExcerpt.length > best.length ? ev.reasoningExcerpt : best;
      }, null);

      // Check if existing before upsert (to count new creates)
      const existingRow = selectExisting.get(sessionId, triggerUuid);
      const isNew = !existingRow;

      upsertChangeSetNoReturn.run(
        sessionId,
        project,
        tsStart,
        tsEnd,
        triggerUuid,
        lastEvent.messageUuid,
        triggerUserPrompt,
        reasoningExcerpt,
        ctx.branch,
        ctx.worktree_path,
        ctx.pr_number,
        ctx.shipyard_task,
        now,
      );

      if (isNew) changeSetsCreated++;

      // Resolve change_set id
      const csRow = selectExisting.get(sessionId, triggerUuid);
      if (!csRow) continue; // should not happen
      const changeSetId = csRow.id;

      for (const ev of groupEvents) {
        const toolInputJson = JSON.stringify(ev.toolInput);
        insertFileChange.run(
          changeSetId,
          sessionId,
          ev.ts,
          ev.toolName,
          ev.filePath,
          ev.changeKind,
          ev.messageUuid,
          toolInputJson,
        );
        const afterChanges = (db.query('SELECT changes() AS n').get() as { n: number }).n;
        if (afterChanges > 0) fileChangesInserted++;
      }
    }
  });

  tx();

  return { changeSetsCreated, fileChangesInserted };
}

// ---------------------------------------------------------------------------
// Read helpers (for server.ts §5)
// ---------------------------------------------------------------------------

export function getSessionContext(sessionId: string): SessionContextRow | null {
  const db = getDb();
  return db.query<SessionContextRow, [string]>(
    'SELECT * FROM session_context WHERE session_id = ?',
  ).get(sessionId) ?? null;
}

export function getChangeSetCount(sessionId: string): number {
  const db = getDb();
  const row = db.query<{ n: number }, [string]>(
    'SELECT COUNT(*) AS n FROM change_sets WHERE session_id = ?',
  ).get(sessionId);
  return row?.n ?? 0;
}

export function listChangeSets(filters: AgentChangesFilters): ChangeSetRow[] {
  const db = getDb();
  const conditions: string[] = [];
  const params: (string | number)[] = [];

  if (filters.session_id) {
    conditions.push('cs.session_id = ?');
    params.push(filters.session_id);
  }
  if (filters.since !== undefined) {
    conditions.push('cs.ts_start >= ?');
    params.push(filters.since);
  }
  if (filters.until !== undefined) {
    conditions.push('cs.ts_start <= ?');
    params.push(filters.until);
  }
  if (filters.branch) {
    conditions.push('cs.branch = ?');
    params.push(filters.branch);
  }
  if (filters.pr !== undefined) {
    conditions.push('cs.pr_number = ?');
    params.push(filters.pr);
  }
  if (filters.shipyard_task) {
    conditions.push('cs.shipyard_task = ?');
    params.push(filters.shipyard_task);
  }

  const where = conditions.length > 0 ? `WHERE ${conditions.join(' AND ')}` : '';
  const limit = Math.min(filters.limit ?? 25, 100);

  if (filters.file_path) {
    // Join with file_changes for path substring filter
    const pathParam = `%${filters.file_path}%`;
    const sql = `
      SELECT DISTINCT cs.*
      FROM change_sets cs
      JOIN file_changes fc ON fc.change_set_id = cs.id
      ${where ? where + ' AND' : 'WHERE'} fc.file_path LIKE ?
      ORDER BY cs.ts_start DESC
      LIMIT ?
    `;
    params.push(pathParam, limit);
    return db.query<ChangeSetRow, (string | number)[]>(sql).all(...params);
  }

  const sql = `SELECT cs.* FROM change_sets cs ${where} ORDER BY cs.ts_start DESC LIMIT ?`;
  params.push(limit);
  return db.query<ChangeSetRow, (string | number)[]>(sql).all(...params);
}

// ---------------------------------------------------------------------------
// Rationale backfill helpers (for WS4 summary-pass integration)
// ---------------------------------------------------------------------------

/**
 * Return change_sets for the session that have both trigger_user_prompt or
 * reasoning_excerpt set, and rationale IS NULL. Ordered oldest-first so
 * the backfill processes turns in chronological order.
 */
export function listChangeSetsNeedingRationale(
  sessionId: string,
): Array<{ id: number; trigger_user_prompt: string | null; reasoning_excerpt: string | null }> {
  const db = getDb();
  return db
    .query<
      { id: number; trigger_user_prompt: string | null; reasoning_excerpt: string | null },
      [string]
    >(
      `SELECT id, trigger_user_prompt, reasoning_excerpt
       FROM change_sets
       WHERE session_id = ? AND rationale IS NULL
         AND (trigger_user_prompt IS NOT NULL OR reasoning_excerpt IS NOT NULL)
       ORDER BY ts_start ASC`,
    )
    .all(sessionId);
}

/**
 * Set rationale for a single change_set by id. Only writes when the current
 * rationale IS NULL (never overwrites a populated value — belt-and-suspenders
 * on top of the WHERE clause in listChangeSetsNeedingRationale).
 */
export function backfillRationale(changeSetId: number, rationale: string): void {
  const db = getDb();
  db.query(
    `UPDATE change_sets SET rationale = ? WHERE id = ? AND rationale IS NULL`,
  ).run(rationale, changeSetId);
}

export function listFileChanges(changeSetIds: number[]): Record<number, FileChangeRow[]> {
  if (changeSetIds.length === 0) return {};
  const db = getDb();
  const placeholders = changeSetIds.map(() => '?').join(', ');
  const rows = db.query<FileChangeRow, number[]>(
    `SELECT * FROM file_changes WHERE change_set_id IN (${placeholders}) ORDER BY ts ASC`,
  ).all(...changeSetIds);

  const result: Record<number, FileChangeRow[]> = {};
  for (const row of rows) {
    const existing = result[row.change_set_id];
    if (existing) {
      existing.push(row);
    } else {
      result[row.change_set_id] = [row];
    }
  }
  return result;
}
