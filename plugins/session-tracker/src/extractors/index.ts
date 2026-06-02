import type { AgentSession } from '../types.js';
import { extractClaudeSessions } from './claude.js';
import { extractCursorSessions } from './cursor.js';

export function extractAll(): AgentSession[] {
  return [...extractClaudeSessions(), ...extractCursorSessions()];
}
