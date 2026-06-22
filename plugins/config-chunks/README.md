# config-chunks

A **package manager for agent-instruction guidance**. Shared agent guidance —
git policy, coding conventions, workflow rules — usually lives as copy-pasted
blocks in each person's global instruction file (`~/.claude/CLAUDE.md`,
`~/.claude/AGENTS.md`): tribal lore that silently drifts.

This plugin distributes named, versioned blocks of guidance ("chunks") that
reconcile into each user's host instruction file(s). The chunk format and the
assembled bundle are **provider-agnostic** — the bundle wires into Claude Code's
`CLAUDE.md` (by `@import`) and into the universal `AGENTS.md` substrate that
Codex, Cursor, Gemini CLI, Copilot and ~any AGENTS.md-reading agent load.

The **automatic** reconcile lifecycle (refresh on every session) is Claude-native
today, via a `SessionStart` hook. On other hosts the same engine runs — you just
trigger the reconcile yourself (one command / alias / git hook). See
[Host support](#host-support) for exactly what's automated where.

## How it works

```
contributing plugin                 ~/.claude/chunks/               host file(s)
  chunks/*.md  ──publish-chunks.sh──▶ registered/<owner>.<name>.md
                                            │
                                     reconcile.sh
                                            │
                                            ▼
                                       bundle.md  ─┬─@import──▶ CLAUDE.md  (claude target)
                                                   └─inlined──▶ AGENTS.md  (agents target)
```

- **Push model.** Each contributing plugin publishes its own chunks to a shared
  drop dir (`~/.claude/chunks/registered/`) via a SessionStart hook. The
  registry never scans sibling plugin directories — only documented surfaces.
- **`install = subscribe`, `uninstall = unsubscribe`.** A disabled/uninstalled
  plugin stops re-publishing → its chunk goes stale → the reconciler prunes it.
- **One marker-wrapped block per host file.** The reconciler maintains a single
  block between `<!-- config-chunks:start -->` / `<!-- config-chunks:end -->`
  markers, then owns `bundle.md` wholesale.
- **Boring & instant.** The SessionStart reconcile is TTL + content-hash gated;
  it exits in a few ms unless the registered chunk set actually changed.

## The chunk contract

A chunk is a markdown file with YAML frontmatter and a body:

```yaml
---
name: my-chunk-name      # unique kebab-case slug; the bundle dedup key
version: 1.0.0           # semver; bumps trigger a reconcile before the TTL
owner: config-chunks     # kebab-case slug of the owning plugin
order: 50                # integer sort key (0-20 first, 40-60 normal, 80-100 last)
summary: One-line human description for review + catalog purposes.
# optional progressive-disclosure keys:
disclosure: inline       # `inline` (default) or `pointer`
skill: my-procedure      # required iff disclosure: pointer
---

Body content — injected verbatim into the bundle.
```

- **`name`** is the dedup key: two plugins shipping the same `name` collapse to
  one, highest `version` wins.
- **`owner`** names the published file: `registered/<owner>.<name>.md`.
- Both `name` and `owner` must be kebab-case (enforced by `publish-chunks.sh`).

### Size gates + progressive disclosure

The bundle is **always-on context tax** — every chunk costs tokens in every
session for every subscriber. Two body-size caps (chars; ~4 chars/token):

- `disclosure: inline` (default) → **≤ 2000 chars**, full body rendered.
- `disclosure: pointer`          → **≤ 400 chars**. The body is a 1-3 line
  *rule*; the heavy how-to lives in a sibling `skill`, loaded on demand. The
  reconciler renders a compact stub:

  ```
  ## my-chunk-name
  **<summary>**

  <1-3 line rule body>

  → For the full procedure, use the `my-procedure` skill.
  ```

The `chunk-review` skill is the **hard gate** at authoring time (over-cap →
`drop`). `reconcile.sh` only **warns** at runtime (stderr) — bundles are never
silently mutilated.

See `templates/chunk.template.md` and `templates/pointer-chunk.template.md`.

## How targets work

`targets:` in `~/.claude/config/chunks.yaml` selects which host instruction
file(s) the reconciler maintains:

- **`claude`** → adds an `@import ~/.claude/chunks/bundle.md` line inside the
  marker block in `~/.claude/CLAUDE.md`. The bundle is loaded by reference.
- **`agents`** → inlines the bundle **body** between the markers in the AGENTS.md
  target (no `@import` support there). Resolved path: env
  `CONFIG_CHUNKS_AGENTS_MD` → else `agents_path:` scalar in chunks.yaml → else
  `~/.claude/AGENTS.md`. **On a non-Claude host you must set `agents_path` (or
  `CONFIG_CHUNKS_AGENTS_MD`) to your host's real file** — e.g. `~/.codex/AGENTS.md`
  or `<project>/AGENTS.md`. The `~/.claude/AGENTS.md` fallback is read only by
  Claude Code; no other agent loads it, so leaving the default on Codex/Cursor
  writes the bundle to a file nothing reads.

With **no `targets:` key** the reconciler auto-detects: `claude` if CLAUDE.md
exists, `agents` if the AGENTS.md target exists; neither → defaults to `claude`.

## Host support

The artifact is provider-agnostic; the **automation** around it varies by host.
Two things differ per host: **placement** (does the reconcile run automatically?)
and **path** (where the bundle is written).

| Host | Bundle wired via | Auto-refresh | Setup |
|---|---|---|---|
| **Claude Code** (CLI/Desktop/IDE) | `@import` in `~/.claude/CLAUDE.md` | ✅ `SessionStart` hook | Install the plugin — nothing else. |
| **Codex / Cursor / Gemini / Copilot / any AGENTS.md host** | bundle body inlined in `AGENTS.md` | ⚠️ manual trigger | Set `agents_path` to your host's `AGENTS.md`, then run the reconcile (below). |

**Auto-refresh is Claude-only** because `SessionStart` is a Claude Code hook event;
no cross-host equivalent exists. Everywhere else the *same* engine produces the
*same* bundle — you just run it yourself. Two notes:

- **Interactive changes already self-reconcile** on every host: any
  `chunks-config.sh` mutation (`add-chunk`, `set-targets`, …) runs publish +
  reconcile immediately. The manual step only matters for picking up **new
  versions of foreign chunks** between sessions.
- To refresh on demand (alias it, or wire it into a shell/`git` hook):

  ```bash
  # PLUGIN_DIR = wherever the plugin is installed (Claude sets $CLAUDE_PLUGIN_ROOT;
  # on other hosts, point it at the plugin dir yourself).
  bash "$PLUGIN_DIR/scripts/publish-chunks.sh" && \
  bash "$PLUGIN_DIR/scripts/reconcile.sh"
  ```

config-chunks keeps its own state (config, registry, `bundle.md`) under
`~/.claude/` regardless of host — that's just its data directory, not a Claude
dependency. The inlined `AGENTS.md` body is self-contained, so your non-Claude
host never needs to read anything under `~/.claude/`.

## Opting in

First-party chunks are **opt-in**; foreign-plugin chunks are always-on. Manage
your opt-in via `~/.claude/config/chunks.yaml` — but don't hand-edit it (the
parser is picky about block form). Use the `chunks-config.sh` engine:

```bash
ENGINE="$CLAUDE_PLUGIN_ROOT/scripts/chunks-config.sh"
bash "$ENGINE" list
bash "$ENGINE" doctor
bash "$ENGINE" add-group    <name>
bash "$ENGINE" remove-group <name>
bash "$ENGINE" toggle-group <name>
bash "$ENGINE" add-chunk    <slug>
bash "$ENGINE" remove-chunk <slug>
bash "$ENGINE" toggle-chunk <slug>
bash "$ENGINE" add-target   <claude|agents>      # append one target (idempotent)
bash "$ENGINE" set-targets  <claude|agents>...   # replace the whole targets list
bash "$ENGINE" set-agents-path <path>            # AGENTS.md the `agents` target writes (required off Claude)
```

The engine is idempotent, ensures the config exists, and auto-runs
publish + reconcile after every mutation so the change lands immediately (no
session restart). `set-targets` / `add-target` validate that each value is
`claude` or `agents` and reject anything else.

Or, inside your agent, just say *"subscribe me to <group>"* / *"what chunks am
I on"* / *"set my targets to claude and agents"* — the `chunks` skill (and
`/ai-setup`) drive the engine for you.

**Block-list form is required.** The reconciler uses BSD-awk-compatible YAML
parsing; inline list syntax (`groups: [a, b]`) is **not supported** and silently
yields no results. `doctor` flags the inline-form footgun.

### Groups

A **group** (`groups/<name>.yaml`) bundles related chunk slugs for one-shot
opt-in. Copy `templates/group.template.yaml`, list chunk `name` slugs under
`chunks:` in block form. Nested groups are not supported — list slugs directly.
Unknown slugs produce a stderr warning and are skipped.

## The SessionStart hook

Wire a SessionStart hook (see `hooks/hooks.json`) that runs, in order:

1. `publish-chunks.sh` — copies this plugin's `chunks/*.md` into the shared drop
   dir as `registered/<owner>.<name>.md`, stamping a fresh mtime.
2. `reconcile.sh` — prunes stale chunks, dedups by version, sorts by `order`,
   assembles `bundle.md`, and maintains the marker block in each active target.

## Uninstalling

`bundle.md` lives outside the plugin dir, so run `scripts/uninstall.sh` after
uninstalling the plugin. It removes the bundle, stamp, and this plugin's
registered chunk files, and strips the managed marker block from **both** the
CLAUDE.md and AGENTS.md targets. (There is no plugin-uninstall hook event, so
this step is manual.) Your `~/.claude/config/chunks.yaml` opt-in selections and
any foreign-plugin chunks are preserved.

## Tuning

- **Sync TTL** (`reconcile.sh`, default 24h) — fast-path skip window.
- **Prune TTL** (`reconcile.sh`, default 14d) — how long an unrefreshed chunk
  survives before being dropped. Must exceed the largest realistic gap between
  sessions so hook-ordering lag never prunes a live chunk.
