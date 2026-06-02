import { openSync, readSync, closeSync, statSync } from 'node:fs';

export interface ParsedMessage {
  uuid: string;
  ts: number;
  role: 'user' | 'assistant';
  text: string;
}

/** Per-assistant-message token usage, keyed by the API message id. */
export interface ParsedUsage {
  messageId: string;
  model: string | null;
  ts: number;
  inputTokens: number;
  outputTokens: number;
  cacheCreationTokens: number;
  cacheReadTokens: number;
}

export type ChangeKind =
  | 'file_edit'      // Edit
  | 'file_write'     // Write
  | 'notebook_edit'  // NotebookEdit
  | 'git'            // Bash git …
  | 'gh'             // Bash gh …
  | 'shipyard'       // mcp__*shipyard*__* tool call
  | 'other_tool';    // captured-but-uncategorized (reserved; not inserted by default)

export interface ParsedToolEvent {
  messageUuid: string;
  ts: number;
  toolName: string;
  changeKind: ChangeKind;
  filePath: string | null;
  toolInput: Record<string, unknown>;
  triggerMessageUuid: string | null;
  triggerUserPrompt: string | null;
  reasoningExcerpt: string | null;
}

export interface ParsedJsonl {
  sessionId: string | null;
  project: string | null;
  messages: ParsedMessage[];
  toolEvents: ParsedToolEvent[];
  usages: ParsedUsage[];
  bytesRead: number;
  lastMessageUuid: string | null;
}

const MAX_TEXT_PER_MESSAGE = 8000;

function flattenContent(content: unknown): string {
  if (typeof content === 'string') return content;
  if (!Array.isArray(content)) return '';
  const parts: string[] = [];
  for (const block of content) {
    if (!block || typeof block !== 'object') continue;
    const b = block as Record<string, unknown>;
    if (b.type === 'text' && typeof b.text === 'string') {
      parts.push(b.text);
    } else if (b.type === 'tool_use') {
      const name = typeof b.name === 'string' ? b.name : 'tool';
      let inputStr = '';
      try {
        inputStr = JSON.stringify(b.input ?? {});
      } catch {}
      if (inputStr.length > 1000) inputStr = inputStr.slice(0, 1000) + '…';
      parts.push(`[tool_use:${name}] ${inputStr}`);
    }
  }
  return parts.join('\n');
}

function isIgnorable(text: string): boolean {
  if (!text.trim()) return true;
  if (text.startsWith('<local-command-caveat>')) return true;
  if (text.startsWith('<command-name>')) return true;
  if (text.startsWith('<command-message>')) return true;
  if (text.startsWith('<command-stdout>')) return true;
  if (text.startsWith('<command-stderr>')) return true;
  if (text.startsWith('<local-command-stdout>')) return true;
  if (text.startsWith('<local-command-stderr>')) return true;
  return false;
}

/** Extract the first non-env-var token from a shell command string. */
function firstShellToken(command: string): string {
  // Strip leading VAR=val assignments before the real command
  const tokens = command.trim().split(/\s+/);
  for (const token of tokens) {
    if (/^[A-Z_][A-Z0-9_]*=/.test(token)) continue;
    return token;
  }
  return '';
}

/** Extract the subcommand (second non-env-var token) for git/gh synthetic paths. */
function secondShellToken(command: string): string {
  const tokens = command.trim().split(/\s+/);
  let skip = true;
  for (const token of tokens) {
    if (skip && /^[A-Z_][A-Z0-9_]*=/.test(token)) continue;
    if (skip) { skip = false; continue; } // skip the command itself (git/gh)
    return token;
  }
  return '';
}

/** Classify a tool_use block, returning null if it should be skipped. */
function classifyToolUse(
  name: string,
  input: Record<string, unknown>,
): { changeKind: ChangeKind; filePath: string | null; toolInput: Record<string, unknown> } | null {
  if (name === 'Edit') {
    const fp = typeof input['file_path'] === 'string' ? input['file_path'] : null;
    return { changeKind: 'file_edit', filePath: fp, toolInput: { file_path: fp } };
  }
  if (name === 'Write') {
    const fp = typeof input['file_path'] === 'string' ? input['file_path'] : null;
    return { changeKind: 'file_write', filePath: fp, toolInput: { file_path: fp } };
  }
  if (name === 'NotebookEdit') {
    const fp =
      typeof input['notebook_path'] === 'string'
        ? input['notebook_path']
        : typeof input['file_path'] === 'string'
          ? input['file_path']
          : null;
    return { changeKind: 'notebook_edit', filePath: fp, toolInput: { file_path: fp } };
  }
  if (name === 'Bash') {
    const command = typeof input['command'] === 'string' ? input['command'] : '';
    const cmd = firstShellToken(command);
    if (cmd === 'git') {
      const sub = secondShellToken(command);
      return {
        changeKind: 'git',
        filePath: `git:${sub}`,
        toolInput: { command: command.length > 500 ? command.slice(0, 500) + '…' : command },
      };
    }
    if (cmd === 'gh') {
      const sub = secondShellToken(command);
      return {
        changeKind: 'gh',
        filePath: `gh:${sub}`,
        toolInput: { command: command.length > 500 ? command.slice(0, 500) + '…' : command },
      };
    }
    return null; // non-VCS bash: skip
  }
  if (name.startsWith('mcp__') && /shipyard/i.test(name)) {
    const shipyardInput: Record<string, unknown> = {};
    if (input['task_id'] !== undefined) shipyardInput['task_id'] = input['task_id'];
    if (input['title'] !== undefined) shipyardInput['title'] = input['title'];
    if (input['status'] !== undefined) shipyardInput['status'] = input['status'];
    return { changeKind: 'shipyard', filePath: name, toolInput: shipyardInput };
  }
  return null; // all other tools: skip
}

export function parseJsonl(path: string, fromByte: number = 0): ParsedJsonl {
  const stat = statSync(path);
  const out: ParsedJsonl = {
    sessionId: null,
    project: null,
    messages: [],
    toolEvents: [],
    usages: [],
    bytesRead: fromByte,
    lastMessageUuid: null,
  };
  if (fromByte >= stat.size) return out;

  const fd = openSync(path, 'r');
  try {
    const length = stat.size - fromByte;
    const buf = Buffer.allocUnsafe(length);
    readSync(fd, buf, 0, length, fromByte);
    const text = buf.toString('utf8');
    const lines = text.split('\n');
    const lastIsPartial = !text.endsWith('\n');
    const completeLines = lastIsPartial ? lines.slice(0, -1) : lines;
    const partialBytes = lastIsPartial ? Buffer.byteLength(lines[lines.length - 1]!, 'utf8') : 0;
    out.bytesRead = stat.size - partialBytes;

    // Rolling last-user-turn tracker for triggerMessageUuid population
    let lastUser: { uuid: string; text: string } | null = null;
    // Rolling reasoning tracker: most recent assistant text within the current
    // user turn. Claude Code often emits reasoning text and the tool_use in
    // SEPARATE assistant messages, so we fall back to this when a tool_use's own
    // message carries no text. Reset at each user-turn boundary so reasoning from
    // an unrelated earlier turn can't bleed in.
    let lastAssistantText: string | null = null;

    for (const line of completeLines) {
      if (!line) continue;
      let event: Record<string, unknown>;
      try {
        event = JSON.parse(line) as Record<string, unknown>;
      } catch {
        continue;
      }
      if (!out.sessionId && typeof event['sessionId'] === 'string') {
        if (event['isSidechain'] === true && typeof event['agentId'] === 'string') {
          out.sessionId = `${event['sessionId']}:agent-${event['agentId']}`;
        } else {
          out.sessionId = event['sessionId'];
        }
      }
      if (!out.project && typeof event['cwd'] === 'string') out.project = projectNameFromCwd(event['cwd'] as string);

      if (event['isMeta'] === true) continue;
      if (event['type'] !== 'user' && event['type'] !== 'assistant') continue;
      if (!event['message']) continue;

      const role = event['type'] as 'user' | 'assistant';
      const message = event['message'] as Record<string, unknown>;

      // Capture token usage off assistant messages BEFORE any content-based skip:
      // a pure-reasoning message flattens to empty text (and would be dropped below)
      // yet still consumes tokens. Streaming emits the same message.id across several
      // lines carrying identical usage; dedup is handled on write (INSERT OR REPLACE
      // keyed on message_id), so pushing duplicates here is harmless.
      if (role === 'assistant' && message && typeof message['usage'] === 'object' && message['usage'] !== null) {
        const messageId = typeof message['id'] === 'string' ? message['id'] : null;
        if (messageId) {
          const u = message['usage'] as Record<string, unknown>;
          const num = (v: unknown): number => (typeof v === 'number' && Number.isFinite(v) ? v : 0);
          const usageTs = typeof event['timestamp'] === 'string' ? Date.parse(event['timestamp'] as string) : Date.now();
          out.usages.push({
            messageId,
            model: typeof message['model'] === 'string' ? (message['model'] as string) : null,
            ts: Number.isNaN(usageTs) ? Date.now() : usageTs,
            inputTokens: num(u['input_tokens']),
            outputTokens: num(u['output_tokens']),
            cacheCreationTokens: num(u['cache_creation_input_tokens']),
            cacheReadTokens: num(u['cache_read_input_tokens']),
          });
        }
      }

      let messageText = flattenContent(message?.['content']);

      if (role === 'user') {
        const c = message?.['content'];
        if (Array.isArray(c) && c.every((b: unknown) => {
          const bl = b as Record<string, unknown> | null;
          return bl?.['type'] === 'tool_result';
        })) continue;
      }

      if (isIgnorable(messageText)) continue;
      if (messageText.length > MAX_TEXT_PER_MESSAGE) {
        messageText = messageText.slice(0, MAX_TEXT_PER_MESSAGE) + '…';
      }

      const uuid = typeof event['uuid'] === 'string' ? event['uuid'] : '';
      const ts = typeof event['timestamp'] === 'string' ? Date.parse(event['timestamp'] as string) : Date.now();
      if (!uuid || Number.isNaN(ts)) continue;

      out.messages.push({ uuid, ts, role, text: messageText });
      out.lastMessageUuid = uuid;

      // Update rolling lastUser tracker for non-ignorable user turns; reset the
      // reasoning tracker so the next assistant text is scoped to this new turn.
      if (role === 'user') {
        lastUser = { uuid, text: messageText };
        lastAssistantText = null;
      }

      // Extract typed tool events from assistant messages
      if (role === 'assistant') {
        const content = message?.['content'];
        if (!Array.isArray(content)) continue;

        // Collect reasoning text from text-type blocks on this message
        let reasoningParts: string[] = [];
        for (const block of content) {
          if (!block || typeof block !== 'object') continue;
          const b = block as Record<string, unknown>;
          if (b['type'] === 'text' && typeof b['text'] === 'string') {
            reasoningParts.push(b['text'] as string);
          }
        }
        const rawReasoning = reasoningParts.join('\n');
        const ownReasoning = rawReasoning.length > 0
          ? (rawReasoning.length > 2000 ? rawReasoning.slice(0, 2000) + '…' : rawReasoning)
          : null;
        // Refresh the rolling reasoning tracker whenever this message carries text,
        // so a later tool_use-only message in the same turn can fall back to it.
        if (ownReasoning) lastAssistantText = ownReasoning;
        const reasoningExcerpt = ownReasoning ?? lastAssistantText;

        for (const block of content) {
          if (!block || typeof block !== 'object') continue;
          const b = block as Record<string, unknown>;
          if (b['type'] !== 'tool_use') continue;

          const toolName = typeof b['name'] === 'string' ? b['name'] : '';
          if (!toolName) continue;

          const rawInput = (b['input'] !== null && b['input'] !== undefined && typeof b['input'] === 'object')
            ? (b['input'] as Record<string, unknown>)
            : {};

          const classified = classifyToolUse(toolName, rawInput);
          if (!classified) continue;

          out.toolEvents.push({
            messageUuid: uuid,
            ts,
            toolName,
            changeKind: classified.changeKind,
            filePath: classified.filePath,
            toolInput: classified.toolInput,
            triggerMessageUuid: lastUser?.uuid ?? null,
            triggerUserPrompt: lastUser?.text ?? null,
            reasoningExcerpt,
          });
        }
      }
    }
  } finally {
    closeSync(fd);
  }

  return out;
}

function projectNameFromCwd(cwd: string): string {
  const parts = cwd.split('/').filter(Boolean);
  return parts[parts.length - 1] ?? cwd;
}
