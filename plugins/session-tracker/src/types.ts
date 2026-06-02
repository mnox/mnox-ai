import { z } from 'zod';

export type SessionStatus = 'active' | 'idle' | 'completed' | 'abandoned';
export type SessionSource = 'claude' | 'cursor' | 'codex';

export interface AgentSession {
  id: string;
  shortId: string;
  source: SessionSource;
  cwd: string;
  projectName: string;
  branch: string | null;
  status: SessionStatus;
  startedAt: string;
  lastActivityAt: string;
  endedAt: string | null;
  messageCount: number;
  toolCalls: number;
  agentsSpawned: number;
  title: string | null;
  summary: string | null;
  firstPrompt: string | null;
  model: string | null;
  inputTokens: number;
  outputTokens: number;
  cacheCreationTokens: number;
  cacheReadTokens: number;
  totalTokens: number;
  tags: string[];
  notes: string | null;
}

export interface SessionOverlay {
  id: string;
  source: SessionSource;
  title: string | null;
  tags: string[];
  notes: string | null;
}

export interface OverlayState {
  version: 2;
  overlays: SessionOverlay[];
}

export const SessionStatusSchema = z.enum(['active', 'idle', 'completed', 'abandoned', 'all']);
export const SessionSourceSchema = z.enum(['claude', 'cursor', 'codex', 'all']);

export const SessionListInputSchema = z
  .object({
    status: SessionStatusSchema.default('all').describe(
      'Filter by status: "active" | "idle" | "completed" | "abandoned" | "all"'
    ),
    source: SessionSourceSchema.default('all').describe('Filter by source: "claude" | "cursor" | "codex" | "all"'),
    project: z.string().optional().describe('Filter by project name (partial match)'),
    since: z
      .string()
      .optional()
      .describe('ISO 8601 date/datetime — only sessions with lastActivityAt >= since (e.g. "2026-05-01" or "2026-05-01T00:00:00Z")'),
    until: z
      .string()
      .optional()
      .describe('ISO 8601 date/datetime — only sessions with lastActivityAt <= until'),
    limit: z.number().int().min(1).max(100).default(20).describe('Max results (1-100, default: 20)'),
    format: z.enum(['markdown', 'json']).default('markdown').describe('Output format: "markdown" | "json"'),
  })
  .strict();

export const SessionGetInputSchema = z
  .object({
    id: z.string().min(1).describe('Session ID (full UUID or 8-char shortId)'),
  })
  .strict();

export const SessionUpdateInputSchema = z
  .object({
    id: z.string().optional().describe('Session ID (defaults to matching current cwd)'),
    title: z.string().optional().describe('Human-readable session title'),
    tags: z.array(z.string()).optional().describe('Tags like "bug", "feature"'),
    notes: z.string().optional().describe('Freeform notes'),
    status: z.literal('completed').optional().describe('Only "completed" allowed (to end session)'),
  })
  .strict();

export const SessionCleanupInputSchema = z
  .object({
    older_than_days: z.number().int().min(1).default(7).describe('Archive sessions older than N days (default: 7)'),
    dry_run: z.boolean().default(true).describe('Preview without archiving (default: true)'),
  })
  .strict();

export const SessionSearchInputSchema = z
  .object({
    query: z.string().min(1).describe('Free-text query. Words you remember from the session.'),
    mode: z
      .enum(['lexical', 'semantic', 'hybrid'])
      .default('hybrid')
      .describe('lexical = FTS only, semantic = embeddings only, hybrid = both fused (default)'),
    scope: z
      .enum(['chunks', 'summaries', 'both'])
      .default('both')
      .describe('chunks = message-level, summaries = session-level summaries, both (default)'),
    project: z.string().optional().describe('Filter by project name (partial match)'),
    since_days: z
      .number()
      .int()
      .min(1)
      .optional()
      .describe('Restrict to sessions active in the last N days (ignored if `since` is provided)'),
    since: z
      .string()
      .optional()
      .describe('ISO 8601 date/datetime — only hits with ts >= since. Takes precedence over since_days.'),
    until: z
      .string()
      .optional()
      .describe('ISO 8601 date/datetime — only hits with ts <= until.'),
    limit: z.number().int().min(1).max(50).default(10).describe('Max sessions returned (1-50, default: 10)'),
  })
  .strict();

export const SessionTokenStatsInputSchema = z
  .object({
    project: z.string().optional().describe('Filter by project name (partial match)'),
    since: z
      .string()
      .optional()
      .describe('ISO 8601 date/datetime — only usage with ts >= since (e.g. "2026-01-01")'),
    until: z.string().optional().describe('ISO 8601 date/datetime — only usage with ts <= until'),
    group_by: z
      .enum(['model', 'project', 'both', 'none'])
      .default('both')
      .describe('Breakdown dimension(s) to include alongside the grand total (default: both)'),
    format: z.enum(['markdown', 'json']).default('markdown').describe('Output format: "markdown" | "json"'),
  })
  .strict();

export const SetSessionLabelInputSchema = z
  .object({
    label: z
      .string()
      .min(1)
      .max(40)
      .describe('2–3 word descriptor for the current task (shown in Warp tab title)'),
  })
  .strict();

export const AgentChangesInputSchema = z
  .object({
    session_id: z.string().optional().describe('Full UUID, sidechain id, or 8-char shortId. Omit for cross-session.'),
    since: z.string().optional().describe('ISO 8601 — only change_sets with ts_start >= since'),
    until: z.string().optional().describe('ISO 8601 — only change_sets with ts_start <= until'),
    file_path: z.string().optional().describe('Substring match on file_changes.file_path'),
    branch: z.string().optional().describe('Exact match on change_sets.branch'),
    pr: z.number().int().optional().describe('Match change_sets.pr_number'),
    shipyard_task: z.string().optional().describe('e.g. "CX-160" — match change_sets.shipyard_task'),
    limit: z.number().int().min(1).max(100).default(25).describe('Max change_sets (1-100, default: 25)'),
    format: z.enum(['markdown', 'json']).default('markdown').describe('Output format'),
  })
  .strict();

export const SessionConfigGetInputSchema = z.object({}).strict();

export const SessionConfigSetInputSchema = z
  .object({
    enabled: z
      .boolean()
      .optional()
      .describe('Master switch for semantic/embeddings features. Default OFF.'),
    mode: z
      .enum(['off', 'openai', 'local'])
      .optional()
      .describe(
        'Embeddings backend: "off" (lexical only), "openai" (uses OPENAI_API_KEY, sends text to OpenAI, has cost), or "local" (local embedder at ONS_EMBED_URL, no egress, no cost)'
      ),
    prompted: z
      .boolean()
      .optional()
      .describe('Whether the user has already been asked once about enabling semantic search'),
  })
  .strict();

export type AgentChangesInput = z.infer<typeof AgentChangesInputSchema>;

export type SessionListInput = z.infer<typeof SessionListInputSchema>;
export type SessionGetInput = z.infer<typeof SessionGetInputSchema>;
export type SessionUpdateInput = z.infer<typeof SessionUpdateInputSchema>;
export type SessionCleanupInput = z.infer<typeof SessionCleanupInputSchema>;
export type SessionSearchInput = z.infer<typeof SessionSearchInputSchema>;
export type SessionTokenStatsInput = z.infer<typeof SessionTokenStatsInputSchema>;
export type SetSessionLabelInput = z.infer<typeof SetSessionLabelInputSchema>;
export type SessionConfigGetInput = z.infer<typeof SessionConfigGetInputSchema>;
export type SessionConfigSetInput = z.infer<typeof SessionConfigSetInputSchema>;
