import type { ParsedMessage } from './jsonl-parser.js';

export interface Chunk {
  ts_start: number;
  ts_end: number;
  first_message_uuid: string;
  last_message_uuid: string;
  text: string;
  token_count: number;
}

const TARGET_TOKENS = 500;
const OVERLAP_TOKENS = 100;

export function estimateTokens(text: string): number {
  return Math.ceil(text.length / 4);
}

function formatMessage(m: ParsedMessage): string {
  return `[${m.role}] ${m.text}`;
}

export function chunkMessages(messages: ParsedMessage[]): Chunk[] {
  if (messages.length === 0) return [];

  const formatted = messages.map((m) => ({
    msg: m,
    body: formatMessage(m),
    tokens: estimateTokens(formatMessage(m)),
  }));

  const chunks: Chunk[] = [];
  let start = 0;
  while (start < formatted.length) {
    let end = start;
    let tokens = 0;
    while (end < formatted.length && tokens + formatted[end]!.tokens <= TARGET_TOKENS) {
      tokens += formatted[end]!.tokens;
      end++;
    }
    if (end === start) {
      end = start + 1;
      tokens = formatted[start]!.tokens;
    }

    const slice = formatted.slice(start, end);
    chunks.push({
      ts_start: slice[0]!.msg.ts,
      ts_end: slice[slice.length - 1]!.msg.ts,
      first_message_uuid: slice[0]!.msg.uuid,
      last_message_uuid: slice[slice.length - 1]!.msg.uuid,
      text: slice.map((s) => s.body).join('\n\n'),
      token_count: tokens,
    });

    if (end >= formatted.length) break;

    let overlap = 0;
    let nextStart = end;
    while (nextStart > start + 1 && overlap < OVERLAP_TOKENS) {
      nextStart--;
      overlap += formatted[nextStart]!.tokens;
    }
    start = nextStart;
  }

  return chunks;
}
