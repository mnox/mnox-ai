---
name: coding-style
version: 0.1.0
owner: config-chunks
order: 60
summary: Self-documenting code, match the surrounding idiom, stay type-safe with no any-escape, push the design forward.
---

## Coding Style

- **Code should document itself.** Comment only when the code genuinely cannot
  speak for itself — to explain a non-obvious *why*, not to narrate the *what*.
  Comments that restate the line below them are noise that rots out of sync.
- **Match the surrounding idiom.** Follow the naming, structure, and conventions
  already established in the file and module you're touching. Consistency with
  the local code beats importing your own preferred style.
- **Be skeptical of type and struct declarations.** Assume they may be wrong;
  back-reference the real types in the code you touch and keep every change
  type-safe. Never reach for an `any`-equivalent escape hatch to silence the type
  checker — that defeats the one tool that catches the error before runtime.
- **Push the design forward.** Don't add legacy or back-compatibility shims for
  their own sake. Correct the broken interface rather than preserving it behind a
  compatibility layer that calcifies the mistake.

Leave the code better-shaped than you found it, in the grain of what's there.
