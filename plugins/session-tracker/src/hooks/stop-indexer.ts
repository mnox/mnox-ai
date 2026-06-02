#!/usr/bin/env bun
import { readFileSync } from 'node:fs';
import { indexSession, indexAll } from '../indexer.js';
import { heartbeat, getTabLabel } from '../presence.js';
import { deriveRepo, writeTabTitle, formatTabTitle, logTabDebug } from '../tab-title.js';

interface HookPayload {
  hook_event_name?: string;
  session_id?: string;
  transcript_path?: string;
  cwd?: string;
}

async function main(): Promise<void> {
  const payloadPath = process.argv[2];
  const capturedTty = process.argv[3] || null;
  let payload: HookPayload = {};
  try {
    if (payloadPath) {
      payload = JSON.parse(readFileSync(payloadPath, 'utf8')) as HookPayload;
    } else {
      const raw = readFileSync(0, 'utf8');
      if (raw.trim()) payload = JSON.parse(raw) as HookPayload;
    }
  } catch (err) {
    console.error('[stop-indexer] failed to parse payload:', err);
  }

  const start = Date.now();
  try {
    if (payload.session_id) {
      try {
        heartbeat(payload.session_id, capturedTty);
      } catch (err) {
        console.error('[stop-indexer] heartbeat failed:', err);
      }

      // Per-turn tab title re-assert.
      // capturedTty is the live tty re-derived this turn from $PPID (the claude
      // parent) — always correct, never a stale DB value.  Look up the label by
      // that same tty: the set_session_label tool persisted it keyed by the
      // server's own tty (== this claude's tty), so it survives session_id churn
      // on resume/compaction where the session_id no longer matches.
      try {
        if (!capturedTty) {
          logTabDebug('stop-reassert', { ok: false, reason: 'null-tty' });
        } else {
          const label = getTabLabel(capturedTty);
          if (label) {
            const cwd = payload.cwd ?? process.cwd();
            const repo = deriveRepo(cwd);
            const title = formatTabTitle(repo, label);
            const result = writeTabTitle(capturedTty, title);
            logTabDebug('stop-reassert', result, { tty: capturedTty, title });
          } else {
            logTabDebug('stop-reassert', { ok: false, reason: 'no-label' }, { tty: capturedTty });
          }
        }
      } catch (err) {
        // Never let a title-write failure kill the indexer
        console.error('[stop-indexer] tab title re-assert failed:', err);
      }

      const result = await indexSession(payload.session_id);
      console.error(
        `[stop-indexer] session ${payload.session_id.slice(0, 8)} ` +
          `msgs=${result.messagesIndexed} chunks=${result.chunksAdded} ` +
          `embedded=${result.chunksEmbedded} summary=${result.summariesGenerated} ` +
          `(${Date.now() - start}ms)`
      );
    } else {
      const result = await indexAll();
      console.error(
        `[stop-indexer] full sweep files=${result.filesScanned}/${result.filesUpdated} ` +
          `msgs=${result.messagesIndexed} chunks=${result.chunksAdded} ` +
          `embedded=${result.chunksEmbedded} summaries=${result.summariesGenerated} ` +
          `(${Date.now() - start}ms)`
      );
    }
  } catch (err) {
    console.error('[stop-indexer] error:', err);
    process.exit(1);
  }
}

void main();
