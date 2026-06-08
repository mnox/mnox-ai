import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname } from 'node:path';
import { CONFIG_FILE } from './paths.js';

export type EmbeddingsMode = 'off' | 'openai' | 'local';

export interface EmbeddingsConfig {
  enabled: boolean;
  mode: EmbeddingsMode;
  prompted: boolean;
}

export interface SessionTrackerConfig {
  embeddings: EmbeddingsConfig;
}

function defaults(): SessionTrackerConfig {
  return { embeddings: { enabled: false, mode: 'off', prompted: false } };
}

/**
 * Read the on-disk config. Tolerates a missing or corrupt file by returning the
 * (semantic-OFF) defaults. Only recognized keys are surfaced — unknown fields in
 * the file are ignored so a malformed shape can never poison behavior.
 */
export function getConfig(): SessionTrackerConfig {
  try {
    if (existsSync(CONFIG_FILE)) {
      const raw = JSON.parse(readFileSync(CONFIG_FILE, 'utf8')) as Partial<{
        embeddings: Partial<EmbeddingsConfig>;
      }>;
      const base = defaults();
      const e = raw.embeddings ?? {};
      return {
        embeddings: {
          enabled: typeof e.enabled === 'boolean' ? e.enabled : base.embeddings.enabled,
          mode:
            e.mode === 'off' || e.mode === 'openai' || e.mode === 'local'
              ? e.mode
              : base.embeddings.mode,
          prompted: typeof e.prompted === 'boolean' ? e.prompted : base.embeddings.prompted,
        },
      };
    }
  } catch {}
  return defaults();
}

/**
 * Deep-merge `patch` into the embeddings block, persist to disk, and return the
 * new full config. Creates the parent directory if missing.
 */
export function setConfig(patch: Partial<EmbeddingsConfig>): SessionTrackerConfig {
  const current = getConfig();
  const next: SessionTrackerConfig = {
    embeddings: {
      enabled: patch.enabled ?? current.embeddings.enabled,
      mode: patch.mode ?? current.embeddings.mode,
      prompted: patch.prompted ?? current.embeddings.prompted,
    },
  };

  const dir = dirname(CONFIG_FILE);
  if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
  writeFileSync(CONFIG_FILE, JSON.stringify(next, null, 2));
  return next;
}

/** True only when semantic features are explicitly enabled AND a real backend is selected. */
export function embeddingsActive(): boolean {
  const { embeddings } = getConfig();
  return embeddings.enabled === true && embeddings.mode !== 'off';
}
