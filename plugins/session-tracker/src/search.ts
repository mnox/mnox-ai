import { getDb, unpackF32, cosine } from './db.js';
import { embed, EMBED_MODEL_CHUNKS, EMBED_MODEL_SUMMARIES } from './openai-client.js';
import { embeddingsActive } from './config.js';

export type SearchMode = 'lexical' | 'semantic' | 'hybrid';
export type SearchScope = 'chunks' | 'summaries' | 'both';

export interface SearchHit {
  session_id: string;
  project: string | null;
  ts: number;
  source: 'chunk' | 'summary';
  snippet: string;
  score: number;
}

export interface SearchOptions {
  query: string;
  mode?: SearchMode;
  scope?: SearchScope;
  project?: string;
  since?: number;
  until?: number;
  limit?: number;
}

const RRF_K = 60;
const TOP_PER_SOURCE = 50;

function escapeFtsQuery(q: string): string {
  const tokens = q
    .split(/\s+/)
    .map((t) => t.replace(/["()*]/g, ''))
    .filter(Boolean);
  if (tokens.length === 0) return '""';
  return tokens.map((t) => `"${t}"`).join(' OR ');
}

function ftsChunkSearch(query: string, project?: string, since?: number, until?: number): SearchHit[] {
  const db = getDb();
  const ftsQuery = escapeFtsQuery(query);
  const params: any[] = [ftsQuery];
  let where = "session_messages MATCH ?";
  if (project) {
    where += ' AND project LIKE ?';
    params.push(`%${project}%`);
  }
  if (since) {
    where += ' AND ts >= ?';
    params.push(since);
  }
  if (until) {
    where += ' AND ts <= ?';
    params.push(until);
  }
  params.push(TOP_PER_SOURCE);
  try {
    const rows = db
      .query(
        `SELECT session_id, project, ts, message_uuid,
                snippet(session_messages, 5, '«', '»', '…', 16) AS snip,
                bm25(session_messages) AS score
         FROM session_messages
         WHERE ${where}
         ORDER BY score
         LIMIT ?`
      )
      .all(...params) as Array<{
      session_id: string;
      project: string | null;
      ts: number;
      message_uuid: string;
      snip: string;
      score: number;
    }>;
    return rows.map((r) => ({
      session_id: r.session_id,
      project: r.project,
      ts: r.ts,
      source: 'chunk' as const,
      snippet: r.snip,
      score: -r.score,
    }));
  } catch {
    return [];
  }
}

function ftsSummarySearch(query: string, project?: string, since?: number, until?: number): SearchHit[] {
  const db = getDb();
  const tokens = query
    .toLowerCase()
    .split(/\s+/)
    .filter(Boolean);
  if (tokens.length === 0) return [];

  const params: any[] = [];
  const likeClauses = tokens.map(() => 'LOWER(summary) LIKE ?').join(' OR ');
  for (const t of tokens) params.push(`%${t}%`);
  let where = `(${likeClauses})`;
  if (project) {
    where += ' AND project LIKE ?';
    params.push(`%${project}%`);
  }
  if (since) {
    where += ' AND generated_at >= ?';
    params.push(since);
  }
  if (until) {
    where += ' AND generated_at <= ?';
    params.push(until);
  }
  const rows = db
    .query(
      `SELECT session_id, project, generated_at, summary FROM session_summaries WHERE ${where} LIMIT ?`
    )
    .all(...params, TOP_PER_SOURCE) as Array<{
    session_id: string;
    project: string | null;
    generated_at: number;
    summary: string;
  }>;
  return rows.map((r) => ({
    session_id: r.session_id,
    project: r.project,
    ts: r.generated_at,
    source: 'summary' as const,
    snippet: r.summary.slice(0, 240),
    score: 1,
  }));
}

async function vectorChunkSearch(query: string, project?: string, since?: number, until?: number): Promise<SearchHit[]> {
  const db = getDb();
  const result = await embed(EMBED_MODEL_CHUNKS, [query]);
  if (!result || result.length === 0) return [];
  const queryVec = new Float32Array(result[0]!.embedding);

  const params: any[] = [];
  let where = "e.model = ?";
  params.push(EMBED_MODEL_CHUNKS);
  if (project) {
    where += ' AND c.project LIKE ?';
    params.push(`%${project}%`);
  }
  if (since) {
    where += ' AND c.ts_end >= ?';
    params.push(since);
  }
  if (until) {
    where += ' AND c.ts_end <= ?';
    params.push(until);
  }
  const rows = db
    .query(
      `SELECT c.id, c.session_id, c.project, c.ts_end, c.text, e.vec
       FROM chunks c JOIN embeddings e ON e.chunk_id = c.id
       WHERE ${where}`
    )
    .all(...params) as Array<{
    id: number;
    session_id: string;
    project: string | null;
    ts_end: number;
    text: string;
    vec: Buffer;
  }>;

  const scored = rows
    .map((r) => ({
      session_id: r.session_id,
      project: r.project,
      ts: r.ts_end,
      source: 'chunk' as const,
      snippet: r.text.length > 240 ? r.text.slice(0, 240) + '…' : r.text,
      score: cosine(queryVec, unpackF32(r.vec)),
    }))
    .sort((a, b) => b.score - a.score)
    .slice(0, TOP_PER_SOURCE);
  return scored;
}

async function vectorSummarySearch(query: string, project?: string, since?: number, until?: number): Promise<SearchHit[]> {
  const db = getDb();
  const result = await embed(EMBED_MODEL_SUMMARIES, [query]);
  if (!result || result.length === 0) return [];
  const queryVec = new Float32Array(result[0]!.embedding);

  const params: any[] = [];
  let where = 'vec IS NOT NULL AND model = ?';
  params.push('gpt-4o-mini');
  if (project) {
    where += ' AND project LIKE ?';
    params.push(`%${project}%`);
  }
  if (since) {
    where += ' AND generated_at >= ?';
    params.push(since);
  }
  if (until) {
    where += ' AND generated_at <= ?';
    params.push(until);
  }
  const rows = db
    .query(`SELECT session_id, project, generated_at, summary, vec FROM session_summaries WHERE ${where}`)
    .all(...params) as Array<{
    session_id: string;
    project: string | null;
    generated_at: number;
    summary: string;
    vec: Buffer | null;
  }>;
  return rows
    .filter((r) => r.vec)
    .map((r) => ({
      session_id: r.session_id,
      project: r.project,
      ts: r.generated_at,
      source: 'summary' as const,
      snippet: r.summary.slice(0, 240),
      score: cosine(queryVec, unpackF32(r.vec!)),
    }))
    .sort((a, b) => b.score - a.score)
    .slice(0, TOP_PER_SOURCE);
}

function rrfFuse(rankings: SearchHit[][]): SearchHit[] {
  const byKey = new Map<string, SearchHit & { fused: number }>();
  for (const ranking of rankings) {
    ranking.forEach((hit, rank) => {
      const key = `${hit.source}:${hit.session_id}:${hit.ts}`;
      const existing = byKey.get(key);
      const contribution = 1 / (RRF_K + rank + 1);
      if (existing) {
        existing.fused += contribution;
      } else {
        byKey.set(key, { ...hit, fused: contribution });
      }
    });
  }
  return Array.from(byKey.values())
    .sort((a, b) => b.fused - a.fused)
    .map(({ fused, ...rest }) => ({ ...rest, score: fused }));
}

function dedupeBySession(hits: SearchHit[]): SearchHit[] {
  const seen = new Set<string>();
  const out: SearchHit[] = [];
  for (const h of hits) {
    if (seen.has(h.session_id)) continue;
    seen.add(h.session_id);
    out.push(h);
  }
  return out;
}

export async function searchSessions(opts: SearchOptions): Promise<SearchHit[]> {
  const requestedMode: SearchMode = opts.mode ?? 'hybrid';
  const scope: SearchScope = opts.scope ?? 'both';
  const limit = opts.limit ?? 10;

  // Semantic search is opt-in and OFF by default. When inactive we make NO
  // embedding/network calls and collapse any requested 'semantic'/'hybrid' mode
  // down to pure lexical FTS.
  const semanticOn = embeddingsActive();
  const mode: SearchMode = semanticOn ? requestedMode : 'lexical';

  const lexical: SearchHit[] = [];
  const semantic: SearchHit[] = [];

  if (mode === 'lexical' || mode === 'hybrid') {
    if (scope === 'chunks' || scope === 'both') {
      lexical.push(...ftsChunkSearch(opts.query, opts.project, opts.since, opts.until));
    }
    if (scope === 'summaries' || scope === 'both') {
      lexical.push(...ftsSummarySearch(opts.query, opts.project, opts.since, opts.until));
    }
  }

  if (mode === 'semantic' || mode === 'hybrid') {
    if (scope === 'chunks' || scope === 'both') {
      const v = await vectorChunkSearch(opts.query, opts.project, opts.since, opts.until);
      semantic.push(...v);
    }
    if (scope === 'summaries' || scope === 'both') {
      const v = await vectorSummarySearch(opts.query, opts.project, opts.since, opts.until);
      semantic.push(...v);
    }
  }

  let merged: SearchHit[];
  if (mode === 'hybrid') {
    merged = rrfFuse([lexical, semantic]);
  } else if (mode === 'lexical') {
    merged = lexical.sort((a, b) => b.score - a.score);
  } else {
    merged = semantic.sort((a, b) => b.score - a.score);
  }

  return dedupeBySession(merged).slice(0, limit);
}
