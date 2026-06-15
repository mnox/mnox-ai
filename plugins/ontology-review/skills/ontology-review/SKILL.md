---
name: ontology-review
description: Use when reviewing or auditing a knowledge graph, ontology, or schema-for-an-ontology for structural health before bad modeling corrupts inference. Triggers — /ontology-review, 'review the ontology/graph', 'check my schema for an ontology', 'audit the memory graph structure', or deciding whether a set of concepts is modeled correctly. Runs a structured seven-axis review (orthogonality, granularity, taxonomic hygiene, identity and rigidity, relationship semantics, competency questions, inference safety), grounded in OntoClean meta-properties, the OOPS! pitfall catalogue, Grüninger and Fox competency questions, and Gómez-Pérez consistency/completeness/conciseness dimensions. Produces a severity-ranked findings list led by inference-corrupting issues — each with the smell, the offending concept/edge, why it is a problem, and a concrete fix.
---

# Ontology Review

## Overview

Audit a knowledge graph or ontology for structural health and flag the modeling
defects that corrupt inference *before* they get baked in. The review runs across
seven axes in a fixed order, because earlier axes feed later ones (granularity
errors surface *as* orthogonality violations; identity and relationship-semantics
defects are what make inference unsafe). Output is a prioritized findings list,
led by the issues that cause the system to assert wrong facts confidently.

## Quick Reference

| # | Axis | Catches | Grounding |
|---|------|---------|-----------|
| 1 | **Orthogonality** | Concepts that fuse independent axes (the `RedLargeTruck` smell) | OOPS! P01 (polysemy), P07 (merged concepts) |
| 2 | **Granularity** | One concept doing several jobs (too coarse) *and* falsely-split concepts that co-vary (too fine) | OOPS! P07; Gómez-Pérez conciseness |
| 3 | **Taxonomic hygiene** | is-a vs has-a vs part-of confusion; subclassing where composition/relation is meant; tangled multiple inheritance | OOPS! P03, P06, P17; Gómez-Pérez circularity |
| 4 | **Identity & rigidity** | Classes with no identity criterion; classes mixing rigid and anti-rigid membership | OntoClean (I, R, U, D) |
| 5 | **Relationship semantics** | Edge types whose transitivity / symmetry / inverse are undeclared where they hold (or declared where they don't) | OOPS! P05, P11, P13, P25, P26, P28, P29 |
| 6 | **Competency questions** | Questions the ontology *must* answer but structurally cannot — incompleteness | Grüninger & Fox |
| 7 | **Inference safety** | FALSE facts that get entailed from the declared edges + rules — highest stakes | OntoClean + OOPS! reasoning pitfalls |

Deep methodology — meta-property notation, the full P01–P41 catalogue, the error
taxonomy — lives in `references/methodology.md`. Load it when a finding needs
precise justification or pitfall classification.

## Inputs

Accept the ontology/graph in whatever form it exists: an OWL/RDFS/Turtle file, a
property-graph schema, JSON-Schema or class definitions used *as* an ontology, a
memory-graph / knowledge-graph dump, or a prose description of the concepts and
their relations. If the target is ambiguous, ask which artifact to review and
whether a specific subgraph is in scope before starting — do not guess the scope
of a structural audit.

For a large graph the seven axes may be delegated one per sub-agent to keep the
main context lean; the axes are interdependent, so a delegated reviewer must
receive the full concept/edge inventory, not a slice.

## The Review (run the axes in order)

### 1. Orthogonality — detect fused axes

A concept is **orthogonally clean** when each of its dimensions can vary
independently. The test: pick any class or edge and ask *"if I changed the value
of one dimension, would I be forced to change another?"* If yes, the concept
fuses independent axes.

- Canonical smell: a class like `RedLargeTruck` that bakes colour + size + vehicle
  into one identity. Adding a colour forces a new class per size per type — a
  combinatorial explosion that is really three independent facets.
- Flag any class **or edge** where one dimension is welded to another.
- **Fix:** split into a base type plus independent **facets** (composition /
  attribution), so each axis varies on its own — `Truck` with `colour` and `size`
  properties, not a class per combination.

### 2. Granularity — one job or several?

For each concept ask: *"is this one job, or several?"* Granularity errors surface
**as** orthogonality violations — use axis 1's findings as the detector here.

- **Too coarse:** one concept doing multiple jobs (fused axes from axis 1, or a
  class whose instances split cleanly into sub-kinds with different identity
  criteria). Split it.
- **Too fine:** concepts split apart that actually **co-vary** — they always
  change together and never appear independently. Merge them (Gómez-Pérez
  conciseness; redundant near-identical definitions).
- The diagnostic for both: do the dimensions vary independently (→ keep split) or
  in lockstep (→ merge)? Independent-but-fused = too coarse; lockstep-but-split =
  too fine.

### 3. Taxonomic hygiene — is-a vs has-a vs part-of

Catch relations mislabelled as subclassing.

- **is-a vs has-a:** `Car has-a Engine` is composition, not subsumption — a Car is
  not a kind of Engine. Misusing `subClassOf` for what is really a property or a
  part-of relation is OOPS! **P03**.
- **part-of vs is-a:** mereological containment (`Wheel part-of Car`) is not is-a.
  Use a `partOf` relation with the right transitivity (see axis 5), not the class
  hierarchy.
- **Tangled multiple inheritance:** a class inheriting from several parents whose
  identity criteria conflict. Flag it; usually one parent is a true type and the
  others are roles or facets that belong on a relation.
- **Cycles** in the hierarchy (A subclass of B … subclass of A) — OOPS! **P06**,
  Gómez-Pérez circularity at distance 0/1/n. Always a defect.

### 4. Identity & rigidity (OntoClean)

For each class, apply the OntoClean meta-properties (notation and constraints in
`references/methodology.md`):

- **Identity:** does the class have a clear **identity criterion** — a rule for
  judging whether two instances are the same? A class that supplies none is a
  non-sortal masquerading as a type ("no entity without identity").
- **Rigidity:** is membership **rigid** (an instance can never stop being a
  member — *Human*) or **anti-rigid** (it can — *Student*, *Employee*, *Active*)?
- **The key flag:** a single class **mixing rigid and anti-rigid properties** — e.g.
  a `Person` class that also encodes `Employee` (a role one enters and leaves).
  This conflates a permanent type with a temporary role. **Fix:** keep the rigid
  type, model the anti-rigid part as a separate role/phase connected by a
  relation.
- **Subsumption check:** an anti-rigid class cannot subsume a rigid one; a class
  carrying one identity criterion cannot subsume one carrying an incompatible one.
  Violations mean the is-a is really constitution or role-of.

### 5. Relationship semantics — declare what holds, only where it holds

For each edge type, pin down its logical properties. Undeclared properties that
*should* hold cause incompleteness; declared properties that *don't* hold cause
false entailments.

- **Transitivity:** does `R(a,b) ∧ R(b,c) ⇒ R(a,c)`? `partOf` and `ancestorOf` are
  transitive; `parentOf` and `directReportOf` are **not**. **Undeclared
  transitivity that holds** is a silent incompleteness; **declared transitivity
  that doesn't hold** is a false-fact generator (OOPS! P29).
- **Symmetry:** `siblingOf` is symmetric; `parentOf` is not. Flag a symmetric
  relationship that also has a declared inverse (OOPS! P26), or one defined as its
  own inverse incorrectly (P25).
- **Inverses:** declare inverse pairs (`parentOf` / `childOf`) where they exist
  (P13), and verify declared inverses are actually inverse (P05).
- **Domain & range:** present and not over-constrained (P11 missing, P18/P19
  over- or multiply-specified).

### 6. Competency questions — can it answer what it must?

Ask the user (or derive from the stated purpose): *"What questions must this
ontology be able to answer?"* Each becomes a **competency question** — a query the
structure must support.

- For each CQ, test whether the current terminology can **express** it and whether
  the edges/rules can **answer** it. Treat the CQ set as an acceptance suite.
- A CQ that can't be expressed or answered = an **incompleteness** finding: name
  the missing concept, edge, or axiom.
- If the user offers no CQs, infer a handful from the ontology's apparent domain
  and state them as assumptions for confirmation.

### 7. Inference safety — does anything FALSE get entailed?

The highest-stakes axis. Given the declared edges, class axioms, and rules,
**simulate the entailments** and look for any *false* fact the system would assert
confidently.

- Walk the transitive/symmetric/inverse closures from axis 5 and the subsumption
  closure from axes 3–4. Does any derived triple state something untrue?
- Classic sources: a `partOf` chain wrongly made transitive across a part-of /
  member-of boundary; a role modelled as a rigid type so instances are entailed to
  belong forever; disjoint classes that share an instance; an over-broad domain
  that types unrelated individuals.
- Every confirmed false entailment is a **Critical** finding — this is where bad
  modeling stops being a maintenance cost and becomes the system asserting wrong
  facts. Lead the report with these.

## Output

Produce a **prioritized, severity-ranked findings list** — no praise padding, no
restating what is fine at length. Lead with the inference-corrupting issues.

Severity: **Critical** (false entailment, or a defect that breaks reasoning) →
**Important** (degrades quality / correctness but not entailment-fatal) → **Minor**
(hygiene, naming, missing annotations). Rank within severity by blast radius.

Each finding uses this structure:

```
### [SEVERITY] <short finding title>
- **Smell:** <the pattern observed, named — e.g. "fused axes", "anti-rigid type", "undeclared transitivity">
- **Where:** <the specific class / edge / axiom — name it exactly>
- **Why it's a problem:** <the concrete consequence; for Critical, the false fact that gets entailed>
- **Fix:** <a specific, actionable correction — the facet split, the role extraction, the property to declare/undeclare>
- **Grounding:** <OntoClean constraint / OOPS! Pxx / CQ that fails / Gómez-Pérez error type>
```

Close with a one-line **verdict** (e.g. "3 Critical, 5 Important — not safe to
infer over until the Critical false-entailments are fixed") and, if useful, the
single highest-leverage fix.

## Common Mistakes

### ❌ Reviewing surface naming instead of inference behaviour

**Problem:** Flagging inconsistent labels and missing annotations while missing a
`partOf` edge wrongly declared transitive that entails false facts.

**Why it's wrong:** Naming is Minor; a false entailment is Critical. A tidy-looking
ontology that asserts wrong facts is worse than a messy one that doesn't.

**Fix:** Always run axis 7 and lead the report with it. Cosmetic findings go last.

### ❌ Treating granularity and orthogonality as separate searches

**Problem:** Hunting for "too coarse" concepts independently of fused-axis
concepts, doing the analysis twice and missing the link.

**Why it's wrong:** A too-coarse concept *is* usually a fused-axis concept. They
are one phenomenon seen from two angles.

**Fix:** Use axis 1's orthogonality findings as the input to axis 2. The
independent-vs-lockstep test resolves both.

### ❌ Recommending a subclass where a role or relation is meant

**Problem:** "Make `Employee` a subclass of `Person`" when employment is a role a
person enters and leaves.

**Why it's wrong:** It welds an anti-rigid role onto a rigid type (OntoClean
violation) and entails that instances are employees forever.

**Fix:** Keep the rigid type; model the role as a separate concept linked by a
relation, with the anti-rigid membership on the role.

### ❌ Declaring transitivity/symmetry "to be safe"

**Problem:** Marking relationships transitive or symmetric by default because it
seems harmless.

**Why it's wrong:** Each wrongly-declared logical property is a false-fact
generator the reasoner applies confidently and silently.

**Fix:** Declare a property only where it provably holds for *every* instance of
the relation; otherwise leave it undeclared and note the limitation.

### ❌ Skipping competency questions because none were given

**Problem:** Auditing structure in a vacuum with no notion of what the ontology is
for.

**Why it's wrong:** Completeness is only definable against the questions the
ontology must answer; without them, incompleteness is invisible.

**Fix:** Ask for competency questions; if none come, infer a handful from the
domain and state them as assumptions to confirm.

## Notes

- The review is **read-only and advisory** — it produces findings and fixes, it
  does not mutate the ontology. Apply fixes as a separate, confirmed step.
- Axis order is load-bearing: 1→2 (granularity reads orthogonality), 3→4 (hygiene
  feeds identity), 5→7 (relationship semantics feeds inference safety). Do not
  reorder.
- The OOPS! pitfall codes, OntoClean notation, and Gómez-Pérez error taxonomy are
  the shared vocabulary — cite them in findings so they are checkable. Full detail
  in `references/methodology.md`.
