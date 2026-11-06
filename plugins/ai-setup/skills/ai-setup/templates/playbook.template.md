# Template — playbook

Fill-in notes — do not copy this section into the output:

- Write the block below to `~/.ai-setup/<profile-slug>/PLAYBOOK.md`.
- It is for the engineer, not the agent: short, concrete, in the order they
  will need it. "Needs you" comes first because nothing else works until it is
  done.
- Every workflow names real commands, real skill names, and real prompts from
  this setup. No generic advice.
- Build the tables from the manifest: only items with status `applied`,
  `verified`, or `needs-human`.
- State plainly what was not verified and what takes effect only after a
  restart.

```markdown
# Working in your <role> setup

Set up <YYYY-MM-DD> for <stack summary with majors>. Host: <host>.
Scope: <personal | repo | both>.

## Needs you (do these first)

- [ ] <Exact step — e.g. "Sign in to the <system> server: run `<command>` or
      use the in-session server menu.">
- [ ] <Exact step — e.g. "Install the <language> language server:
      `<command>`.">
- [ ] Start a new session so installed plugins load.

## What is installed

| What | Where | Loads when | Fills |
|---|---|---|---|
| <skill name> | <path> | <its trigger, in plain words> | <slot> |
| <plugin or server> | <scope> | <always / on demand> | <slot> |
| <hook> | <settings file> | <after every edit / when the agent stops> | <slot> |
| <instruction file> | <path> | every session | <slot> |

Left out on purpose: <item — reason>; <item — reason>.

## How to work here

### Build a feature

1. <Prompt shape that works with this setup, e.g. "Describe the behavior and
   name the route or component; the <skill> skill loads on its own.">
2. <What the agent will do to verify: the loop, concretely.>
3. <Before a PR: the review skill or command to run.>

### Fix a bug

1. <How to hand over the failure: error text, route, failing test.>
2. <How the agent reproduces it with the verification loop.>

### Review

- <The review skill or subagent, and what it checks.>

### <Another recurring task from the work mix>

- <Concrete steps.>

## Check it works (new session)

Try these three prompts. Each should behave as described.

1. "<A prompt that should load a practice skill>" → <what you should see>.
2. "<A prompt that should use the verification loop>" → <what you should see>.
3. "<A prompt that should hit a boundary>" → the agent asks before <operation>.

## Guardrails in place

- Runs without asking: <the allowed commands>.
- Always asks: <operations>.
- Never: <denied operations and reads>.

## Keeping it current

- **After a major upgrade** of <core facets>: re-run `/ai-setup`. Practice
  skills are pinned to versions and are re-researched when a major changes.
- **When something misfires** (a skill does not load, or loads when it should
  not): say so in a session and adjust the skill's description, or re-run
  `/ai-setup` to re-verify.
- **Team changes:** repo-scoped pieces live in the repo and go through review
  like any other change.

## Undo

- Ledger of everything applied: `~/.ai-setup/<profile-slug>/manifest.json`.
- Pre-change copies of every modified file: `~/.ai-setup/<profile-slug>/backups/`.
- Additions to existing files sit between `<!-- ai-setup:start -->` and
  `<!-- ai-setup:end -->` and can be removed as a block.

## Not verified

- <Anything that could not be checked, and why.>
```
