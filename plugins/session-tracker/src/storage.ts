import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { homedir } from 'node:os';
import type { OverlayState, SessionOverlay, SessionSource } from './types.js';

const SESSIONS_DIR = join(homedir(), '.claude', 'sessions');
const STATE_FILE = join(SESSIONS_DIR, 'state.json');

export function loadOverlays(): OverlayState {
  try {
    if (existsSync(STATE_FILE)) {
      const raw = JSON.parse(readFileSync(STATE_FILE, 'utf8'));
      if (raw.version === 2) return raw;
      if (raw.version === 1 && Array.isArray(raw.sessions)) {
        return migrateV1ToV2(raw);
      }
    }
  } catch {}
  return { version: 2, overlays: [] };
}

function migrateV1ToV2(v1: {
  sessions: Array<{ id: string; title: string | null; tags: string[]; notes: string | null }>;
}): OverlayState {
  return {
    version: 2,
    overlays: v1.sessions
      .filter((s) => s.title || s.tags.length > 0 || s.notes)
      .map((s) => ({
        id: s.id,
        source: 'claude' as SessionSource,
        title: s.title,
        tags: s.tags,
        notes: s.notes,
      })),
  };
}

export function saveOverlays(state: OverlayState): void {
  const dir = dirname(STATE_FILE);
  if (!existsSync(dir)) {
    mkdirSync(dir, { recursive: true });
  }
  writeFileSync(STATE_FILE, JSON.stringify(state, null, 2));
}

export function findOverlay(state: OverlayState, id: string, source: SessionSource): SessionOverlay | undefined {
  return state.overlays.find((o) => o.id === id && o.source === source);
}

export function upsertOverlay(
  state: OverlayState,
  id: string,
  source: SessionSource,
  updates: { title?: string; tags?: string[]; notes?: string }
): SessionOverlay {
  let overlay = findOverlay(state, id, source);
  if (!overlay) {
    overlay = { id, source, title: null, tags: [], notes: null };
    state.overlays.push(overlay);
  }
  if (updates.title !== undefined) overlay.title = updates.title;
  if (updates.tags !== undefined) overlay.tags = updates.tags;
  if (updates.notes !== undefined) overlay.notes = updates.notes;
  return overlay;
}

export function removeStaleOverlays(state: OverlayState, validIds: Set<string>): SessionOverlay[] {
  const removed: SessionOverlay[] = [];
  state.overlays = state.overlays.filter((o) => {
    if (validIds.has(`${o.source}:${o.id}`)) return true;
    removed.push(o);
    return false;
  });
  return removed;
}

export function formatDuration(ms: number): string {
  const seconds = Math.floor(ms / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  if (days > 0) return `${days}d ${hours % 24}h`;
  if (hours > 0) return `${hours}h ${minutes % 60}m`;
  if (minutes > 0) return `${minutes}m`;
  return `${seconds}s`;
}

export function formatAge(isoDate: string): string {
  return formatDuration(Date.now() - new Date(isoDate).getTime()) + ' ago';
}
