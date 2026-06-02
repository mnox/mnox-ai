import { extractAll } from './extractors/index.js';
import { loadOverlays, findOverlay } from './storage.js';
import type { AgentSession } from './types.js';

export function reconcile(): AgentSession[] {
  const sessions = extractAll();
  const overlays = loadOverlays();

  for (const session of sessions) {
    const overlay = findOverlay(overlays, session.id, session.source);
    if (!overlay) continue;

    if (overlay.title) session.title = overlay.title;
    if (overlay.tags.length > 0) session.tags = overlay.tags;
    if (overlay.notes) session.notes = overlay.notes;
  }

  sessions.sort((a, b) => new Date(b.lastActivityAt).getTime() - new Date(a.lastActivityAt).getTime());
  return sessions;
}

export function findSession(sessions: AgentSession[], id: string): AgentSession | undefined {
  const lower = id.toLowerCase();
  return sessions.find((s) => s.id === id || s.shortId === lower);
}
