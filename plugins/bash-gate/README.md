# bash-gate

A **PreToolUse gate over Bash** for Claude Code. It auto-allows commands it can
*prove* are safe — so you stop clicking "approve" on the same harmless
`mkdir ~/dev/foo`, `rm` of a git-ignored build artifact, or `cat … 2>/dev/null` —
while still deferring anything dangerous to the normal permission prompt.

It is **deterministic-first**: a registry of narrow allow-classes decides
allow/defer with no network and no LLM. An **optional** LLM arbiter handles the
long tail of "gated" verbs. The hook **always exits 0** — an internal error never
blocks your Bash; it just falls back to the normal prompt.

> ⚠️ **Read this whole file before enabling anything.** This plugin can be
> configured to *auto-approve commands that change your machine* (`rm`, `chmod`,
> `curl` mutations, `kill`). It ships **safe-by-default** — out of the box it
> auto-allows **nothing** by path and the LLM arbiter is **off**. You opt in
> explicitly. Treat that opt-in as a real security decision.
>
> One default worth knowing up front: with the arbiter **off**, the Tier-B
> "gated" verbs (`chmod`, `source`/`.`, `curl` mutations, `scp`, `rsync`,
> `kill`/`killall`/`pkill`) **fail closed to `ask`** — the hook asks you to
> confirm them. That's deliberate (it stops a bypass-mode user silently
> auto-running them), but it means installing the plugin can *add* a confirm
> prompt on those verbs. Enable the arbiter, or trim `gated_patterns`, to change
> that. See [Gated verbs & the `ask` default](#gated-verbs--the-ask-default).

## Who this is for — and why it exists

bash-gate's sweet spot is **`bypassPermissions` mode**. Run Claude Code with
bypass on and nothing prompts — fast, but *naked*: a prompt injection hidden in a
file or web page can silently run a destructive command. The disciplined setup is
to keep a safety net of `ask`/`deny` rules on dangerous Bash **even under bypass**,
and let this gate **auto-approve the provably-safe commands** so the net only ever
catches genuine danger. You get the no-prompt flow *without* running bare. That's
the third path out of approval fatigue — neither "keep clicking approve" nor
"go naked." (See [Running under bypass mode](#running-under-bypass-mode-the-main-case).)

It also works in normal (`default`) mode — there it simply trims the routine
"approve this safe command again?" prompts — but bypass is what it was designed
around.

## How it decides

Every Bash command is split into segments (on `&&`, `||`, `;`, `|`) and each
segment is classified independently. A command is auto-allowed only if **every**
segment is provably safe. Examples of what the deterministic classes recognize:

- writes confined to your configured `dev_roots` (`mkdir`, `touch`, `cp`, `mv`,
  `ln`, `rmdir` of paths under a root you listed)
- `rm` of a git-**tracked-clean** file, or a git-**ignored** build artifact,
  under a dev root (reproducible / recoverable)
- `chmod` with a safe mode (no setuid/setgid/sticky, no world-writable, no
  recursive/symlink flags) on an existing path under a dev root
- safe redirect stripping (`2>/dev/null`, `>/tmp/…`) before classification
- inert verbs in a compound that your settings would never have prompted on

Anything it can't prove safe → **defer** → you get the normal permission prompt.
Pipes, command substitution (`$(…)`, backticks), heredocs, and unknown redirects
all defer. It fails **toward** asking, never away from it.

### Two danger tiers

- **Tier A — always-ask** (`sudo`, `ssh`, `gpg --delete`, `eval`, …): whatever is
  in your Claude `settings.json` `permissions.ask`. The hook **never** auto-approves
  these; it only mirrors the list so a *buried* compound case
  (`cd x && sudo y`) is handled consistently.
- **Tier B — gated** (`chmod`, `source`/`.`, `curl` mutations, `scp`, `rsync`,
  `kill`/`killall`/`pkill`): listed in `gated_patterns` in the config. These are
  handed to the **optional LLM arbiter** — `SAFE` → auto-allow, `UNSAFE` → ask
  with the reason surfaced, any error/disabled → **ask** (fail closed).

## Requirements

- **Claude Code** (this is a Claude-Code-specific PreToolUse hook).
- **Python 3** on your `PATH`.
- **PyYAML** — a hard runtime dependency. The hook reads its config via
  `import yaml`; without it the hook loads no config and auto-allows nothing
  (safe, but the plugin does nothing). Install: `python3 -m pip install --user pyyaml`.
- For the **optional** arbiter only: `ANTHROPIC_API_KEY` in the hook's
  environment + outbound network.

## Install

```
claude plugin install bash-gate@mnox-ai
```

The PreToolUse hook is wired automatically by the plugin's `hooks.json`. Then run
the one-time setup helper (checks deps, seeds your editable user config, prints
the opt-in steps):

```
bash "$(claude plugin root bash-gate)/scripts/bash-gate-setup.sh"
```

(Or run `plugins/bash-gate/scripts/bash-gate-setup.sh` from a clone.)

## Configure

Config resolves in this order (first hit wins):

1. `$BASH_GATE_CONFIG` — an explicit file path
2. `~/.config/bash-gate/config.yaml` — **your** config (survives plugin updates)
3. the shipped `hooks/bash_gate.yaml` — safe defaults

**Edit your user config, not the shipped file** — `claude plugin update` replaces
the plugin tree. The setup script seeds `~/.config/bash-gate/config.yaml` for you.

Opt in by listing your dev roots:

```yaml
# ~/.config/bash-gate/config.yaml
dev_roots:
  - "~/dev"
  - "~/code"
```

Only paths under a `dev_root` are eligible for path-based auto-allow. With
`dev_roots: []` (the shipped default) the path classes never fire.

### Optional: enable the LLM arbiter

```yaml
arbiter:
  enabled: true
  model: "claude-haiku-4-5"
```

…and export `ANTHROPIC_API_KEY` in the hook's environment. Now Tier-B gated verbs
are auto-approved when the arbiter rules them `SAFE`. **This is the powerful,
sharp-edged feature** — an LLM deciding whether to auto-run `chmod`/`curl`/`kill`.
It fails closed (any error/timeout/disabled → ask), but enable it deliberately.

### Gated verbs & the `ask` default

With the arbiter **disabled** (shipped default), a Tier-B gated verb resolves to
an explicit `ask` rather than a silent pass-through. This is a safety choice: a
bypass-mode user who'd moved these verbs out of `permissions.ask` (see below)
would otherwise have them silently auto-run. The trade-off is that a *non*-bypass
user sees an added confirm prompt on `chmod`/`curl`-mutations/`kill`/etc. To tune:

- **Enable the arbiter** (above) — gated verbs get a `SAFE`/`UNSAFE` judgment
  instead of an unconditional ask.
- **Trim `gated_patterns`** in your config — remove a verb you don't want gated
  and the hook stops touching it (your normal `settings.json` governs it again).

### Running under bypass mode (the main case)

This is what bash-gate is built for. Under `defaultMode: bypassPermissions` the
documented precedence is **deny > ask > hook-decision** — so a hook `allow`
**cannot** suppress a `settings.json` `permissions.ask` prompt; it can only add
friction. That's the point for the *deny*/*ask* safety net: keep your genuinely
dangerous verbs in `permissions.ask`/`permissions.deny` and bypass still can't run
them unseen.

For the verbs you want the gate to **auto-approve** (the Tier-B gated set, via the
arbiter), there's one wrinkle: because `ask` outranks a hook `allow`, an
auto-approvable verb must **not** sit in your `permissions.ask` list — move it out,
into the gate's `gated_patterns`, so the hook becomes its sole gate (this is the
"inversion"). Then: arbiter `SAFE` → auto-approve, `UNSAFE`/error → `ask` (fail
closed). Verbs you *don't* move stay a hard `ask` under bypass — exactly the safety
net you want.

**This plugin will not edit your `settings.json`** — that's your security config.
Decide which verbs to move yourself. If you run in normal `default` mode, you don't
need the inversion at all: a hook `allow` auto-approves directly there.

## Telemetry

Every decision is appended as JSONL to `~/.config/bash-gate/bash_gate.log.jsonl`
(override the dir with `BASH_GATE_HOME`). Summarize / prune it:

```
python3 "$(claude plugin root bash-gate)/hooks/bash_gate_stats.py" --since 24h
python3 "$(claude plugin root bash-gate)/hooks/bash_gate_stats.py" --cleanup --retain-days 30
```

## Extending it: `/bash-gate-add`

When a prompt slips through that *should* have been auto-allowed, run
**`/bash-gate-add`** with the offending command. The skill diagnoses it with
`bash_gate.py --explain`, recommends one precise allow-class extension, asks for
your explicit approval, then builds the class plus test fixtures. Deterministic
allow-classes are the right fix for any *recurring* safe pattern; the arbiter is
the catch-all for one-offs.

## Tests

```
python3 plugins/bash-gate/test/run_tests.py
```

The suite is hermetic (a temp `$HOME` sandbox; reads none of your real machine
state) and covers 148 command fixtures plus unit tests for the parser, redirect
stripping, pattern matching, and the arbiter seams.

## Safety summary

- **Never loosens your permissions on install**: empty `dev_roots` + arbiter off
  means it auto-allows nothing. (It *can* add an `ask` on gated verbs — the safe
  direction — see [the gated-verb note](#gated-verbs--the-ask-default).)
- **Fails toward asking** — every uncertain case defers to the normal prompt.
- **Never blocks Bash** — internal errors exit 0 and fall through.
- **Never touches your `settings.json`** — it reads your `ask`/`deny` lists to
  stay consistent, but never writes security config.
- The dangerous capabilities (path auto-allow, the LLM arbiter, the bypass-mode
  inversion) are **all explicit opt-ins**. You own each one.
