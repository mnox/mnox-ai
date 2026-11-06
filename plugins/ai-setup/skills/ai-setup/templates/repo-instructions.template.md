# Template — repo instructions

Fill-in notes — do not copy this section into the output:

- Target file: `AGENTS.md` at the repo root unless the repo already uses a
  host-specific file (`references/instruction-files.md`, "One source of truth").
- Build every line from the repo surveyor's `verified` or `observed` facts.
  Nothing `inferred`, nothing conventional.
- Budget: about 150 lines including imports. Path-specific conventions go into
  scoped rules; procedures and stack knowledge go into practice skills.
- When adding to an existing file, emit only the missing sections, wrapped in
  `<!-- ai-setup:start -->` … `<!-- ai-setup:end -->` at the end of the file.
  When creating the file, no markers are needed.
- Delete any section with nothing verified to say. A short file is the goal.
- No absolute paths, usernames, or secrets.

```markdown
# <Project name>

<One or two lines: what this is and its shape — e.g. "Next.js storefront;
server-rendered routes under `app/`, shared UI in `packages/ui`.">

## Commands

| Task | Command |
|---|---|
| Install | `<verified command>` |
| Dev server | `<verified command>` — serves at `<url>`; ready when `<signal>` |
| Build | `<verified command>` |
| Test (all) | `<verified command>` |
| Test (one file) | `<verified command with a placeholder path>` |
| Lint | `<verified command>` |
| Typecheck | `<verified command>` |
| Format | `<verified command>` |

## Layout

- `<path>` — <what lives here, only if not obvious>
- `<path>` — <generated; do not edit — regenerate with `<command>`>

## Conventions

- <A choice that differs from the ecosystem default.> See `<exemplar path>`.
- <A choice that cannot be inferred from one file.> See `<exemplar path>`.

## Definition of done

Before reporting a change as working:

1. `<typecheck and lint commands>` pass.
2. `<the relevant tests>` pass.
3. <The verification loop: run it and look — e.g. "load the affected route in
   the browser and check the console is clean.">

## Boundaries

- Do not edit `<generated or vendored path>`.
- Ask before <migration, deploy, dependency change, or other blast-radius
  operation> — <the reason>.
- Never read or print `<secret-bearing files, by name>`.

## More context

- <Topic>: `<path to the doc>`
- <Topic>: `<path to the doc>`

## Gotchas

- <A required service, environment setup step, or known-flaky area that has
  actually caused trouble.>
```
