import { spawnSync } from 'node:child_process';
import { openSync, writeSync, closeSync, appendFileSync } from 'node:fs';
import { basename } from 'node:path';
import { TAB_DEBUG_LOG } from './paths.js';

/**
 * Derive the server's OWN controlling tty device path (e.g. "/dev/ttys001").
 *
 * Because the MCP server is usually a per-session child of its host agent, the
 * server shares the parent's tty. We read it from `ps` against our OWN pid;
 * this is unambiguous and needs no session-id or cwd lookup.
 *
 * Returns null when: process has no controlling tty (probe harness, CI),
 * tty field is "?" or "??", or ps fails.
 */
export function ownTtyDevice(): string | null {
  const result = spawnSync('ps', ['-o', 'tty=', '-p', String(process.pid)], {
    encoding: 'utf8',
  });
  const raw = (result.stdout ?? '').trim();
  if (!raw || raw === '?' || raw === '??') return null;
  return raw.startsWith('/dev/') ? raw : `/dev/${raw}`;
}

/**
 * Derive the repo name from a cwd path.
 * Tries `git -C <cwd> rev-parse --show-toplevel`; falls back to basename(cwd).
 * Never throws — errors degrade to the basename fallback.
 */
export function deriveRepo(cwd: string): string {
  try {
    const result = spawnSync('git', ['-C', cwd, 'rev-parse', '--show-toplevel'], {
      encoding: 'utf8',
    });
    if (result.status === 0 && result.stdout.trim()) {
      return basename(result.stdout.trim());
    }
  } catch {
    // fall through to basename
  }
  return basename(cwd) || 'unknown';
}

/**
 * Build the tab title as "[REPO] label" -- the repo name is ALWAYS prefixed,
 * uppercased and bracketed (e.g. "[MAYFLOWER] E2E smoke tests").
 *
 * Warp truncates a tab title at the FIRST ASCII space, so the bracket->label
 * gap AND any space inside a multi-word label would silently drop everything
 * after it. We therefore replace every internal whitespace run with U+00A0
 * (non-breaking space): it renders like a space but is not a truncation point.
 * Verified live 2026-05-27: ASCII spaces truncate, NBSP survives.
 */
export function formatTabTitle(repo: string, label: string): string {
  const NBSP = '\u00A0';
  return `[${repo.toUpperCase()}] ${label}`.replace(/\s+/g, NBSP);
}

/**
 * Outcome of a {@link writeTabTitle} attempt. The feature degrades silently by
 * design (never disrupt the agent loop), so the discriminated reason exists
 * purely to feed {@link logTabDebug} — callers should not surface it to users.
 */
export type TabTitleResult =
  | { ok: true }
  | { ok: false; reason: 'null-tty' | 'not-warp' | 'io-error'; errno?: string };

/**
 * Write an OSC 2 (tab title) escape sequence to the given named tty device.
 *
 * Degrades silently (ok:false) — never throws — when:
 *  - ttyDevice is null/empty                  → reason 'null-tty'
 *  - TERM_PROGRAM !== 'WarpTerminal'          → reason 'not-warp'
 *  - any I/O error (ENXIO, EACCES, gone)      → reason 'io-error' (+ errno)
 *
 * MUST receive the NAMED device path (e.g. "/dev/ttys001"), NOT the /dev/tty
 * alias — the alias fails with ENXIO from a detached process.
 */
export function writeTabTitle(ttyDevice: string | null, title: string): TabTitleResult {
  if (!ttyDevice) return { ok: false, reason: 'null-tty' };
  if (process.env.TERM_PROGRAM !== 'WarpTerminal') return { ok: false, reason: 'not-warp' };
  try {
    const fd = openSync(ttyDevice, 'w');
    try {
      writeSync(fd, `\x1b]2;${title}\x07`);
    } finally {
      closeSync(fd);
    }
    return { ok: true };
  } catch (err) {
    const errno = (err as NodeJS.ErrnoException)?.code;
    return { ok: false, reason: 'io-error', errno };
  }
}

/**
 * Skip/error reason for a tab-title decision. Superset of {@link TabTitleResult}'s
 * reasons — callers may also report `no-label` (re-assert with nothing persisted)
 * before {@link writeTabTitle} is ever invoked. Kept separate so writeTabTitle's
 * own return type stays tight (it can never produce `no-label`).
 */
export type TabLogResult =
  | { ok: true }
  | { ok: false; reason: 'null-tty' | 'not-warp' | 'io-error' | 'no-label'; errno?: string };

/**
 * Emit ONE structured diagnostic line per stop-hook turn / tool call — including
 * the cases where NO write was attempted (`no-label`, `null-tty`). This is the
 * whole point: a session that never sets a label should produce an informative
 * `skip:no-label` line, not silence that's indistinguishable from "logging broken."
 *
 * Routes to the shared hook log so
 * both the MCP-tool path and the stop-hook re-assert path land in one place to
 * `tail`/`grep`. Never throws — logging must not disrupt the agent loop.
 */
export function logTabDebug(
  context: string,
  result: TabLogResult,
  extra: { tty?: string | null; title?: string } = {}
): void {
  try {
    const status = result.ok
      ? 'ok'
      : `skip:${result.reason}${result.errno ? `(${result.errno})` : ''}`;
    const line =
      `[tab-debug] ${new Date().toISOString()} ${context} ` +
      `status=${status} tty=${extra.tty ?? 'null'} title=${JSON.stringify(extra.title ?? '')}\n`;
    appendFileSync(TAB_DEBUG_LOG, line);
  } catch {
    // swallow — never let debug logging disrupt the agent loop
  }
}
