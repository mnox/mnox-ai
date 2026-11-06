# Instruction Files — global and repo-level agent instructions

Instruction files are the only layer loaded on every turn. That makes them the
most valuable place for a small number of lines and the most expensive place for
everything else.

**Contents**
- [The inclusion test](#the-inclusion-test)
- [Global instructions](#global-instructions)
- [Repo instructions](#repo-instructions)
- [One source of truth across hosts](#one-source-of-truth-across-hosts)
- [Merge protocol](#merge-protocol)
- [Writing style](#writing-style)

## The inclusion test

A line stays only if it passes all four:

1. **Always relevant.** True for essentially every task in this scope. If it
   applies to some tasks, it is a skill; to some paths, a scoped rule.
2. **Not inferable.** The agent could not learn it by reading the code or
   running a standard command.
3. **Changes behavior.** Removing it would cause a mistake. "Write clean code"
   fails; "run `pnpm test -- <file>` for a single test" passes.
4. **Not enforceable.** No tool can check it. If one can, configure the tool.

Lines that commonly fail: generic best practices, descriptions of what each file
does, long API documentation, anything that changes weekly, and personas ("you
are a senior engineer").

## Global instructions

Person-scoped: follows the engineer into every repo. This skill writes its
additions inside its managed block and nothing else.

Include:

| Kind | Example |
|---|---|
| Role line | The role and default stack in one or two lines, so an empty repo still gets sensible defaults |
| Working agreements | When to ask versus proceed; commit and push etiquette; how to report completed work |
| Preferences no tool enforces | Naming or structure preferences that hold across the engineer's repos |
| Environment facts | Operating system and shell; the preferred package manager for new projects |
| Pointers | "Stack practice skills are installed; prefer them over general knowledge for `<stack>`" |

Exclude: facts about any one codebase, stack tutorials, anything already
supplied by an installed guidance bundle, and secrets.

Coexisting with a guidance-bundle manager: if the inventory shows another tool's
managed block in the global file (for example `config-chunks`), that tool owns
working-style guidance. Do not edit inside its block and do not restate what its
bundle covers — add only the role-specific lines. If no such tool is present and
the engineer wants a working-style baseline, mention `/chunks-setup`; do not
generate a substitute bundle here.

Use `templates/global-instructions.template.md`.

## Repo instructions

Code-scoped and committed: true for every contributor and every agent host.
Built from the repo surveyor's verified facts, never from convention.

| Section | Content | Rule |
|---|---|---|
| What this is | One or two lines: product, architecture in a phrase | Skip if the name says it |
| Commands | Install, dev, build, test, **single test**, lint, typecheck, format | Only commands that were run successfully. The single-test command matters most |
| Layout | Where things live — only what is not obvious from the tree | A map, not a file listing |
| Conventions | Choices that differ from the ecosystem default or cannot be inferred | Each with an exemplar file path instead of a prose description |
| Definition of done | What to run and observe before claiming a change works | Names the verification loop |
| Boundaries | Generated or vendored paths not to edit; operations that require asking | Mirrors the permission ask and deny rules, with the reason |
| Pointers | Deeper docs, linked or imported — not copied | ADRs, contributing guide, architecture notes |
| Gotchas | Required services, environment setup, known-flaky areas | Only ones that have actually bitten |

Monorepos: the root file holds what is true everywhere; each package that
differs gets its own nested instruction file or path-scoped rule. Scope the
setup to the engineer's part and leave other packages' files alone.

Path-scoped conventions ("under `app/`, components are server components
unless marked") go in the host's scoped-rule mechanism, not the root file —
they load only when those files are in play. See the host adapter for the
format.

Use `templates/repo-instructions.template.md`.

## One source of truth across hosts

`AGENTS.md` is the cross-host convention for repo instructions; several hosts
also have their own file name. Never maintain two copies of the same content.

| Situation | Do |
|---|---|
| Neither file exists | Write the canonical content to `AGENTS.md`. Add the host-specific file only if the host needs it, as a thin file that imports or points to `AGENTS.md` plus host-only extras |
| Only the host-specific file exists | Follow what is there; add to it. Offer the `AGENTS.md` split only if the team uses more than one host |
| Only `AGENTS.md` exists | Add to it. Create the host-specific file only if the host does not read `AGENTS.md` |
| Both exist with different content | Do not merge them silently. Show the divergence in the plan and ask which is canonical |

Which hosts read which file, and how imports work, changes — confirm in the host
adapter and the host's own documentation at run time.

## Merge protocol

For any instruction file that already exists:

1. **Back up** the file to `$STATE/backups/` before anything else.
2. **Read all of it**, including files it imports, and note any managed blocks.
3. **Classify what you intended to add** against what is there:
   - Already present, in any wording → do not add.
   - Absent → add inside the `ai-setup` managed block.
   - Contradicts existing content (the file says `npm test`; the verified
     command is `pnpm test`) → do not change their line. Put the contradiction
     in the plan and let the engineer decide.
4. **Never rewrite, reorder, or reformat** existing content.
5. **Never edit inside another tool's managed block.** Its owner regenerates it.
6. **Place the managed block** at the end of the file unless the host gives
   position meaning.
7. **Re-run** = replace the contents of the `ai-setup` block in place. If the
   block's markers are missing or unbalanced, stop and report rather than
   appending a second block.

A file this skill created from nothing needs no markers; record it in the
manifest as created so a re-run and a rollback both know it is fully owned.

Record a line-budget check for each instruction file in the manifest
(`layer-rules.md`), counting imported files.

## Writing style

- Imperative and specific: "Run `make test-unit` before committing."
- One fact per line; short lists under plain headings.
- Give the reason when it is not obvious — a line with a why is followed more
  reliably and generalizes better than a bare rule.
- Point to an exemplar file rather than describing a pattern in prose.
- Reserve emphasis for the one or two lines that truly must not be missed.
- No absolute paths, usernames, or machine-specific details in committed files.
- Check each line once more against the inclusion test before writing it.
