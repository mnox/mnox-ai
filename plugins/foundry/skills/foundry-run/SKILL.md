---
name: foundry-run
description: >
  Compatibility conductor for Sven-native Unit runtime advancement. Use when
  invoked as `$foundry-run` or `/foundry-run`, when asked to run, drive, advance,
  or continue legacy-named Unit work. Route every new advancement through
  `sven_unit_workflow run`; do not call predecessor tooling.
---

# Foundry Run Compatibility Conductor

This skill name remains for old invocations. The conductor now advances Sven
Unit/PlanIR work through the native runtime command.

```bash
SVEN_HOME="${SVEN_HOME:-$HOME/dev/personal/sven}"
UNIT_BIN="$SVEN_HOME/src-tauri/target/debug/sven_unit_workflow"
```

## Hard Guardrails

- Never push, open a PR, merge to a remote, tag, deploy, message, or call an
  external API from this skill.
- Never write raw SQL.
- Never call predecessor engines or stores for new work.
- Bound each local advancement with `--limit`.
- Stop on any missing approval, missing binary, command failure, or no-progress
  report.

## First Iteration

1. Confirm the binary builds:

   ```bash
   cargo check --manifest-path "$SVEN_HOME/src-tauri/Cargo.toml" --bin sven_unit_workflow
   ```

2. Inspect current pending work through status when a batch id is known:

   ```bash
   "$UNIT_BIN" status --default-db --batch-id <batch-id> --json
   ```

3. Advance only when the current task explicitly authorizes local Sven runtime
   writes:

   ```bash
   "$UNIT_BIN" run --default-db --approve-local-write --enable-runtime-control --limit 1 --json
   ```

## Loop Rule

After each run, inspect JSON output. Continue only when all are true:

- `externalWriteExecuted=false`
- `oldFoundryStoreRead=false`
- `oldFindingsFileStoreUsed=false`
- the run completed at least one Unit or clearly reports no claimable work
- the user asked for a continued local run, or the current task explicitly
  authorized continuing bounded local advancement

## Completion Summary

Report:

```text
SVEN UNIT RUN COMPLETE
Units completed:
Events recorded:
Dispatch receipts:
External effects: false
Predecessor store read: false
Residual risk:
```

If no claimable work remains, stop and say so. Do not emulate lifecycle
transitions outside the native command.
