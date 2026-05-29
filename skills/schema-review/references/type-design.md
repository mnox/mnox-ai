# Lens: In-Code Data Structure & Type Design

Application-code data structures (not DB). Emphasis on Elixir and TypeScript. Make illegal states unrepresentable; parse, don't validate.

## Principles

- **Make illegal states unrepresentable.** A type that can express an impossible combination is a latent bug. Encode state as a sum type, not booleans + optionals.
- **Parse, don't validate.** Consume raw input at the boundary; produce a refined/branded type or fail. Downstream code never re-checks.
- **Algebraic types are the primary tool.** Product types (structs/records) for co-present data; sum types (tagged/discriminated unions) for mutually exclusive states.
- **Primitive obsession is a DDD failure.** `string` is not a `UserId`. Wrap primitives in branded/value types at the domain boundary.
- **No `null`/`nil` sprawl.** Optionality is explicit and intentional (`Option`/`Maybe`/tagged tuples), never nullable-everything.
- Elixir: every public function gets `@spec`; structs over bare maps for domain entities; tagged tuples (`{:ok,_}/{:error,_}`); typed errors over raw strings; `embeds_one/many` for value objects, associations for independently-queryable entities.
- TypeScript: discriminated unions with a literal tag; exhaustiveness via `never`; `readonly`/`as const`; branded types for nominal IDs; never `any`; `satisfies` over `as`.
- **Choose collections by the actual access pattern.** The Big-O of the operation performed (lookup, membership, ordered iteration) drives the choice — not convenience.
- Immutability by default; mutation is a deliberate exception.

## Review checklist

**Illegal states / sum types**
- Struct/record with 2+ booleans whose combinations are partly meaningless → 🟡 MEDIUM (model as tagged union)
- Optional field always present in one state, absent in another → 🟠 HIGH (a sum type wearing optional clothes)
- State-machine logic as if/switch chains over flag combinations → 🟡 MEDIUM (encode as discriminated union + exhaustive switch)
- TS union with no literal discriminant (`kind`/`type`/`tag`) → 🟠 HIGH (fragile narrowing, no exhaustiveness)
- TS switch/if over a union with no `default: const _: never = x` → 🟡 MEDIUM (exhaustiveness unenforced)

**Parse / validation discipline**
- Validation (email/phone/uuid/format) duplicated across call sites → 🟠 HIGH (shotgun parsing → single smart constructor + refined type)
- Function takes `string` where it needs `UserId`/`Email`/`OrgId` → 🟠 HIGH at trust boundaries (primitive obsession → branded type; IDOR risk)
- Input parsed in one layer, re-validated in another → 🟠 HIGH (push to entry boundary)

**Elixir**
- Public function missing `@spec` (esp. `{:ok,_}|{:error,_}` returns) → 🟡 MEDIUM (🔴/🟠 in a shared library)
- `{:error, reason}` where `reason` is a raw string → 🟡 MEDIUM (typed error)
- `try/rescue` for expected business errors → 🟠 HIGH (use result tuples; can mask corruption)
- Domain entity as bare `%{}` map where a struct gives compile-time key safety → 🟠 HIGH (use `defstruct` + `@enforce_keys`)
- `embeds_*` for an entity with independent queries/associations → 🟡 MEDIUM (reconsider as schema + FK)

**TypeScript**
- `any` on a domain type / `as any` / `@ts-ignore` → 🔴 CRITICAL on domain boundaries (use `unknown` + guard)
- `as SomeType` cast with no guard function → 🟠 HIGH (unsafe coercion → smart constructor)
- Never-mutated fields without `readonly`/`Readonly<T>` → 🔵 LOW
- Constant object without `as const satisfies T` → 🔵 LOW (literal types widen to `string`)

**Collections**
- List/array used for by-key lookup in a hot path (`arr.find(x => x.id === id)` in a loop) → 🟡 MEDIUM (O(n)/O(n²) → `Map`)
- Map/object used where only membership is tested → 🔵 LOW (→ `Set`)
- Ordered iteration required but stored in a hash map → 🔵 LOW

## Named anti-patterns

| Name | Signature | Why bad |
|---|---|---|
| **Boolean flag soup** | 3+ `isX`/`hasY` booleans, some combos meaningless | Illegal states; each flag doubles the state space |
| **Stringly typed** | `string` for IDs/statuses/roles; `=== "admin"` scattered | No compile-time safety; typos are runtime bugs |
| **Primitive obsession** | `userId: string`, `amount: number` raw across boundaries | Two different IDs interchangeable to the compiler |
| **Optional fields as states** | `{ pending; result?; error? }` | Encodes impossible combos in optional fields |
| **Shotgun parsing** | Validation duplicated across controller/service/repo | Late-discovered invalidity corrupts partial state |
| **Bare-map domain entity (Elixir)** | Module operates on `%{...}`, no `defstruct` | No enforce_keys; Dialyzer-blind; lost identity |
| **`try/rescue` for business errors (Elixir)** | rescue on an expected failure path | Obscures control flow; callers can't pattern-match |
| **Untagged union (TS)** | `A \| B` with no shared literal tag | Fragile structural narrowing; no exhaustiveness |
| **`any` escape hatch** | `any`/`as any`/`@ts-ignore` on domain types | Opts out of type safety entirely |
| **Wrong collection for access** | `find` in a loop → O(n²) | Silent degradation under load; O(1) exists |

## Severity quick map

- 🔴 CRITICAL: `any` on domain boundary; illegal-state combo reachable in prod; `try/rescue` masking corruption; missing `@spec` on error-returning public API in a shared lib
- 🟠 HIGH: untagged union w/o exhaustiveness; primitive obsession on IDs at a trust boundary; shotgun parsing with partial-mutation risk; bare-map persisted entity; `as` cast w/o guard
- 🟡 MEDIUM: boolean flag soup; stringly-typed status/role; optional-fields-as-states; wrong collection on hot path; missing `@spec` on complex internal fns
- 🔵 LOW: missing `readonly`; `as const` without `satisfies`; embed-vs-assoc with no current correctness issue

## Sources

- [Alexis King — Parse, don't validate](https://lexi-lambda.github.io/blog/2019/11/05/parse-don-t-validate/)
- [F# for Fun and Profit — Making illegal states unrepresentable](https://fsharpforfunandprofit.com/posts/designing-with-types-making-illegal-states-unrepresentable/)
- [Elixir — design anti-patterns](https://hexdocs.pm/elixir/design-anti-patterns.html) · [Typespecs](https://hexdocs.pm/elixir/typespecs.html)
- [TS Handbook — narrowing & discriminated unions](https://www.typescriptlang.org/docs/handbook/2/narrowing.html)
- [Total TypeScript — `satisfies`](https://www.totaltypescript.com/how-to-use-satisfies-operator)
- [Refactoring Guru — Primitive Obsession](https://refactoring.guru/smells/primitive-obsession)
- [Ecto — embedded schemas](https://hexdocs.pm/ecto/embedded-schemas.html)
