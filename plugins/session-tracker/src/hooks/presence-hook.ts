#!/usr/bin/env bun
import { readFileSync } from 'node:fs';
import { recordStart, heartbeat, recordEnd } from '../presence.js';

interface HookPayload {
  hook_event_name?: string;
  session_id?: string;
  transcript_path?: string;
  cwd?: string;
}

async function main(): Promise<void> {
  const mode = process.argv[2] as 'start' | 'heartbeat' | 'end' | undefined;
  const payloadPath = process.argv[3];
  const ttyArg = process.argv[4] || null;
  const ppidArg = process.argv[5] ? Number.parseInt(process.argv[5], 10) : null;

  if (!mode) {
    console.error('[presence-hook] missing mode arg');
    process.exit(1);
  }

  let payload: HookPayload = {};
  try {
    if (payloadPath) {
      payload = JSON.parse(readFileSync(payloadPath, 'utf8')) as HookPayload;
    }
  } catch (err) {
    console.error('[presence-hook] failed to parse payload:', err);
  }

  const sid = payload.session_id;
  if (!sid) {
    console.error('[presence-hook] no session_id in payload');
    process.exit(0);
  }

  try {
    if (mode === 'start') {
      recordStart({ session_id: sid, tty: ttyArg, pid: ppidArg, cwd: payload.cwd ?? null });
      console.error(`[presence-hook] start ${sid.slice(0, 8)} tty=${ttyArg} ppid=${ppidArg}`);
    } else if (mode === 'heartbeat') {
      heartbeat(sid, ttyArg);
      console.error(`[presence-hook] heartbeat ${sid.slice(0, 8)} tty=${ttyArg}`);
    } else if (mode === 'end') {
      recordEnd(sid);
      console.error(`[presence-hook] end ${sid.slice(0, 8)}`);
    }
  } catch (err) {
    console.error('[presence-hook] error:', err);
    process.exit(1);
  }
}

void main();
