import { homedir } from 'node:os';
import { join } from 'node:path';

const HOME = homedir();

export const TRACKER_HOME =
  process.env['SESSION_TRACKER_HOME'] || join(HOME, '.mnox-ai', 'session-tracker');

export const INDEX_DB_PATH =
  process.env['SESSION_TRACKER_DB_PATH'] || join(TRACKER_HOME, 'index.db');

export const CONFIG_FILE =
  process.env['SESSION_TRACKER_CONFIG_PATH'] || join(TRACKER_HOME, 'config.json');

export const STATE_FILE =
  process.env['SESSION_TRACKER_STATE_PATH'] || join(TRACKER_HOME, 'state.json');

export const LOG_DIR =
  process.env['SESSION_TRACKER_LOG_DIR'] || join(TRACKER_HOME, 'logs');

export const TAB_DEBUG_LOG = join(LOG_DIR, 'stop-indexer.log');

export const CLAUDE_PROJECTS_DIR =
  process.env['SESSION_TRACKER_CLAUDE_PROJECTS_DIR'] || join(HOME, '.claude', 'projects');

export const CURSOR_DB_PATH =
  process.env['SESSION_TRACKER_CURSOR_DB_PATH'] ||
  join(HOME, 'Library', 'Application Support', 'Cursor', 'User', 'globalStorage', 'state.vscdb');

export const CODEX_HOME =
  process.env['SESSION_TRACKER_CODEX_HOME'] || join(HOME, '.codex');

export const CODEX_SESSIONS_DIR =
  process.env['SESSION_TRACKER_CODEX_SESSIONS_DIR'] || join(CODEX_HOME, 'sessions');

export const CODEX_SESSION_INDEX_PATH =
  process.env['SESSION_TRACKER_CODEX_SESSION_INDEX_PATH'] || join(CODEX_HOME, 'session_index.jsonl');
