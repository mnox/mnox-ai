import type { AgentSession } from '../types.js';
import { extractClaudeSessions } from './claude.js';
import { extractCodexSessions } from './codex.js';
import { extractCursorSessions } from './cursor.js';

export function extractAll(): AgentSession[] {
  return [...extractClaudeSessions(), ...extractCursorSessions(), ...extractCodexSessions()];
}
