#!/usr/bin/env bash
# bash-gate-setup.sh — one-time, idempotent setup helper for the bash-gate plugin.
#
# What it DOES:
#   - checks python3 + PyYAML (a hard runtime dependency of the hook)
#   - seeds your editable user config at ~/.config/bash-gate/config.yaml
#     (copied from the shipped defaults) so `claude plugin update` never
#     clobbers your settings
#   - prints the OPTIONAL bypass-mode "inversion" guidance
#
# What it deliberately does NOT do:
#   - it NEVER writes your Claude settings.json (your security config is yours).
#     The hook itself is wired automatically by the plugin's hooks.json; the only
#     manual step is the optional bypass-mode inversion, which we only SHOW.
#
# Safe to re-run.
set -euo pipefail

# Resolve the plugin root from this script's location (scripts/ is one level down).
PLUGIN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SHIPPED_YAML="$PLUGIN_ROOT/hooks/bash_gate.yaml"
USER_DIR="${BASH_GATE_HOME:-$HOME/.config/bash-gate}"
USER_CONFIG="$USER_DIR/config.yaml"

say() { printf '%s\n' "$*"; }
hr()  { printf -- '----------------------------------------------------------------\n'; }

hr
say "bash-gate setup"
hr

# 1. python3
if ! command -v python3 >/dev/null 2>&1; then
  say "✗ python3 not found on PATH. The hook is a python3 script and cannot run."
  say "  Install Python 3, then re-run this script."
  exit 1
fi
say "✓ python3: $(python3 --version 2>&1)"

# 2. PyYAML (hard dependency: the hook reads bash_gate.yaml via `import yaml`)
if python3 -c 'import yaml' >/dev/null 2>&1; then
  say "✓ PyYAML present"
else
  say "✗ PyYAML missing — REQUIRED. Without it the hook loads no config and"
  say "  auto-allows nothing (safe, but the plugin does nothing). Install with:"
  say "      python3 -m pip install --user pyyaml"
  say "  (or your distro/venv equivalent), then re-run."
fi

# 3. Seed the user config (idempotent).
mkdir -p "$USER_DIR"
if [ -f "$USER_CONFIG" ]; then
  say "✓ user config already exists: $USER_CONFIG (left untouched)"
else
  cp "$SHIPPED_YAML" "$USER_CONFIG"
  say "✓ seeded user config: $USER_CONFIG"
fi

hr
say "NEXT — opt in (the plugin ships as a no-op for safety):"
say ""
say "  1. Edit $USER_CONFIG and add YOUR dev roots, e.g.:"
say "         dev_roots:"
say "           - \"~/dev\""
say "           - \"~/code\""
say "     Only paths under these roots are eligible for path-based auto-allow."
say ""
say "  2. (Optional) Enable the LLM arbiter for the dangerous \"gated\" verbs"
say "     (chmod, curl mutations, scp, rsync, kill...). Set arbiter.enabled: true"
say "     and export ANTHROPIC_API_KEY in the hook's environment. Read the README"
say "     first — this lets an LLM AUTO-APPROVE those verbs (fail-closed to ask)."
hr
say "OPTIONAL — bypass-permissions users only:"
say ""
say "  If you run Claude Code with defaultMode: bypassPermissions, settings.json"
say "  precedence is deny > ask > hook, so a hook 'allow' CANNOT suppress an 'ask'"
say "  rule. For the arbiter to auto-approve a gated verb, that verb must NOT be in"
say "  your settings.json permissions.ask list. We will NOT edit your settings.json"
say "  for you — review the README's \"bypass-mode inversion\" section and make that"
say "  change yourself if you want it. If you do NOT run bypass mode, ignore this."
hr
# Mark onboarding complete so the SessionStart nudge stays quiet — the user has
# now seen the full opt-in guidance above. Delete this file to see it again.
printf 'bash-gate onboarding shown (via setup)\n' > "$USER_DIR/.onboarded" 2>/dev/null || true
say "Done. The hook is wired automatically via the plugin; no settings.json edit"
say "is required for the deterministic allow-classes to work."
