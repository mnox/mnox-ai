import { getConfig } from './config.js';

export const EMBED_MODEL_CHUNKS = 'text-embedding-3-small';
export const EMBED_MODEL_SUMMARIES = 'text-embedding-3-large';
export const SUMMARY_MODEL = 'gpt-4o-mini';

const API_BASE = 'https://api.openai.com/v1';

function apiKey(): string | null {
  return process.env.OPENAI_API_KEY ?? null;
}

export interface EmbeddingResult {
  index: number;
  embedding: number[];
}

// Local shared embeddings provider. It exposes each configured model as a `type`
// value, so model strings pass through unchanged.
const LOCAL_EMBED_URL = process.env.ONS_EMBED_URL ?? 'http://127.0.0.1:9001/embed';

async function embedViaLocalService(model: string, inputs: string[]): Promise<EmbeddingResult[] | null> {
  try {
    const res = await fetch(LOCAL_EMBED_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ type: model, input: inputs }),
      signal: AbortSignal.timeout(5000),
    });
    if (!res.ok) return null;
    const data = (await res.json()) as { embeddings: number[][] };
    return data.embeddings.map((embedding, index) => ({ index, embedding }));
  } catch {
    return null;
  }
}

async function embedViaOpenAI(model: string, inputs: string[]): Promise<EmbeddingResult[] | null> {
  const key = apiKey();
  if (!key) return null;
  try {
    const res = await fetch(`${API_BASE}/embeddings`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${key}`,
      },
      body: JSON.stringify({ model, input: inputs }),
    });
    if (!res.ok) {
      console.error(`[openai] embed failed: ${res.status} ${await res.text().catch(() => '')}`);
      return null;
    }
    const data = (await res.json()) as { data: Array<{ index: number; embedding: number[] }> };
    return data.data.map((d) => ({ index: d.index, embedding: d.embedding }));
  } catch (err) {
    console.error('[openai] embed error:', err);
    return null;
  }
}

/**
 * Generate embeddings, honoring the user's opt-in config. When embeddings are
 * disabled (the default) this makes NO network calls and returns null so callers
 * fall back to lexical/FTS. When enabled, the selected `mode` picks the backend:
 *   - 'local'  → the local embedder at ONS_EMBED_URL (no egress, no cost)
 *   - 'openai' → the OpenAI embeddings API via OPENAI_API_KEY
 * If the chosen backend is unreachable / unconfigured, returns null (graceful
 * degradation to lexical) rather than crossing over to the other backend.
 */
export async function embed(model: string, inputs: string[]): Promise<EmbeddingResult[] | null> {
  if (inputs.length === 0) return [];
  const { embeddings } = getConfig();
  if (!embeddings.enabled || embeddings.mode === 'off') return null;
  if (embeddings.mode === 'local') return embedViaLocalService(model, inputs);
  return embedViaOpenAI(model, inputs);
}

export interface RationaleInput {
  id: number;
  triggerUserPrompt: string | null;
  reasoningExcerpt: string | null;
}

/**
 * Generate one terse imperative line (≤12 words) per change_set explaining WHY
 * the change was made. Returns a parallel array aligned to the input array, with
 * null entries for any item that could not be parsed from the response.
 * Returns null if the API key is absent or the call fails.
 */
export async function summarizeRationales(items: RationaleInput[]): Promise<string[] | null> {
  if (items.length === 0) return [];
  // Summaries use OpenAI chat completions — only run when explicitly opted into
  // the 'openai' backend. The local embedder has no chat model.
  const { embeddings } = getConfig();
  if (!embeddings.enabled || embeddings.mode !== 'openai') return null;
  const key = apiKey();
  if (!key) return null;

  const userLines = items
    .map(
      (item, i) =>
        `${i + 1}. REQUEST: ${item.triggerUserPrompt ?? '(none)'}\n   REASONING: ${item.reasoningExcerpt ?? '(none)'}`,
    )
    .join('\n');

  try {
    const res = await fetch(`${API_BASE}/chat/completions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${key}`,
      },
      body: JSON.stringify({
        model: SUMMARY_MODEL,
        max_tokens: 30 * items.length,
        temperature: 0.2,
        messages: [
          {
            role: 'system',
            content:
              'You write a single terse imperative line (≤12 words) explaining WHY a ' +
              'code change was made, given the user\'s request and the assistant\'s ' +
              'reasoning. No file names, no fluff, no period. Output one line per ' +
              'numbered item, same numbering.',
          },
          { role: 'user', content: userLines },
        ],
      }),
    });

    if (!res.ok) {
      console.error(`[openai] summarizeRationales failed: ${res.status} ${await res.text().catch(() => '')}`);
      return null;
    }

    const data = (await res.json()) as { choices: Array<{ message: { content: string } }> };
    const responseText = data.choices[0]?.message?.content?.trim() ?? '';

    // Parse numbered lines: "1. text", "2. text", …
    const lines = responseText.split('\n').map((l) => l.trim()).filter((l) => l.length > 0);
    const result: string[] = new Array(items.length).fill('') as string[];
    for (const line of lines) {
      const m = /^(\d+)\.\s+(.+)$/.exec(line);
      if (m) {
        const idx = parseInt(m[1]!, 10) - 1;
        if (idx >= 0 && idx < items.length) {
          result[idx] = m[2]!.trim();
        }
      }
    }
    // Filter empties to null-equivalent: keep only non-empty strings; fill gaps with input-aligned empty
    return result;
  } catch (err) {
    console.error('[openai] summarizeRationales error:', err);
    return null;
  }
}

export async function summarize(text: string): Promise<string | null> {
  // Summaries use OpenAI chat completions — only run when explicitly opted into
  // the 'openai' backend. The local embedder has no chat model.
  const { embeddings } = getConfig();
  if (!embeddings.enabled || embeddings.mode !== 'openai') return null;
  const key = apiKey();
  if (!key) return null;
  try {
    const res = await fetch(`${API_BASE}/chat/completions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${key}`,
      },
      body: JSON.stringify({
        model: SUMMARY_MODEL,
        max_tokens: 220,
        temperature: 0.2,
        messages: [
          {
            role: 'system',
            content:
              'You summarize AI coding-agent transcripts to make them findable later. ' +
              'In 2-4 sentences, capture: what the user was trying to do, the key technical concepts/files/systems involved, and the outcome if any. ' +
              'Use specific keywords (file names, function names, library names, error messages) over generic descriptions. No fluff, no headings.',
          },
          { role: 'user', content: text },
        ],
      }),
    });
    if (!res.ok) {
      console.error(`[openai] summarize failed: ${res.status} ${await res.text().catch(() => '')}`);
      return null;
    }
    const data = (await res.json()) as { choices: Array<{ message: { content: string } }> };
    return data.choices[0]?.message?.content?.trim() ?? null;
  } catch (err) {
    console.error('[openai] summarize error:', err);
    return null;
  }
}
