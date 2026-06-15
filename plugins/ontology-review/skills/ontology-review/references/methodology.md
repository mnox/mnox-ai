# Ontology-Review Methodology Reference

The grounding for each review axis. Four established ontology-evaluation
methodologies, with the correct vocabulary and the constraints a reviewer
checks against. Load this when a finding needs precise justification or when
classifying which pitfall/error a smell maps to.

Sources are listed at the end. Notation and tier assignments are verified
against primary and authoritative secondary sources; transcribe verbatim quotes
from the primary PDFs only when quotation-grade attribution is required.

---

## 1. OntoClean (Guarino & Welty) — identity, rigidity, unity, dependence

A method for validating the **ontological adequacy of subsumption (is-a)
relationships**. Tag each class with four meta-properties, then check every is-a
edge against the subsumption constraints. A violation means the "is-a" is really
something else (constitution, dependence, role-of, …).

**Notation:** each meta-property letter is prefixed with `+` (positive), `−`
(negative), or `~` (anti) — e.g. `+R`, `~U`, `−I`.

### The four meta-properties

- **Rigidity (R)** — grounded in *essential* properties (necessarily true in
  every possible world).
  - `+R` **rigid**: essential to *all* instances; an instance can never stop
    being one (e.g. *Human*, *Physical Object*).
  - `~R` **anti-rigid**: essential to *no* instance; every instance can possibly
    cease to be one (e.g. *Student*, *Caterpillar*).
  - `−R` **non-rigid / semi-rigid**: essential to *some* instances but not
    others. (`~R` is the stricter special case.)
- **Identity (I)** — does the property supply a way to judge two instances
  same-or-different?
  - `+I` **carries** an identity criterion (IC) — a sortal.
  - `+O` **supplies/owns** its *own* IC (`O` = own). `+O ⇒ +I`. Marks where an IC
    *originates* (e.g. *Animal*); load-bearing because ICs inherit downward.
  - `−I` **carries no IC** — a non-sortal / attribution (e.g. *Red*, *Agent*).
  - Governing axiom — *Sortal Individuation*: "no entity without identity" —
    every element instantiates some `+I` property.
- **Unity (U)** — are all instances *wholes* under a common Unity Criterion (UC)?
  - `+U` **carries unity**: all instances must be wholes under one common UC
    (e.g. *Ocean*, *Physical Object*).
  - `~U` **anti-unity**: no instance need be a whole (e.g. *Amount of Matter*).
  - `−U` **no common unity**: instances may be wholes but under *different* UCs
    (e.g. *Legal Agent* spanning persons and companies).
- **Dependence (D)** — external existential dependence.
  - `+D` **externally dependent**: for each instance *x* of φ there necessarily
    exists an instance *y* of ψ that is **neither a part nor a constituent of**
    *x* (the "external" qualifier is the point).
  - `−D` not externally dependent.

### Subsumption constraints (when superclass *q* subsumes subclass *p*)

1. **Rigidity:** an anti-rigid class cannot subsume a rigid one →
   **`~R` cannot subsume `+R`** (*Student* cannot subsume *Human*).
2. **Identity:** if *q* carries an IC, *p* must carry the *same* IC. Properties
   carrying **incompatible ICs are disjoint** and cannot stand in subsumption.
3. **Unity:** if *q* carries a UC, *p* must carry the *same* UC. Incompatible UCs
   are disjoint → **`~U` cannot subsume `+U`**.
4. **Dependence:** a dependent (`+D`) property cannot subsume an independent
   (`−D`) one.

General rule: `+I, +O, +U, ~U, ~R, +D` **inherit downward** (the subclass must
keep them); `−I, −U, −R, −D` do not.

### Applying it

1. **Tag** every class per its *intended meaning*.
2. **Check each is-a edge** against the four constraints; a violation is a
   modeling error — fix the tag or the link.
3. Most violations are a subsumption that is really **constitution** (a living
   being is *constituted of* matter, not a *kind of* matter — `~U` over `+U`).
4. **Backbone first:** analyze the rigid (`+R`) sortals — they form the invariant
   skeleton; roles, phases, and attributions hang off it.

**Mixed rigid/anti-rigid flag (the prompt's axis 4):** a class whose instances'
membership is sometimes permanent and sometimes not is conflating a `+R` sortal
with a `~R` role/phase — split the role out (composition) from the rigid type.

---

## 2. OOPS! — OntOlogy Pitfall Scanner (Poveda-Villalón et al.)

A catalogue of **41 modeling pitfalls (P01–P41, contiguous)**, each tagged
Critical / Important / Minor. Use it as the shared vocabulary for naming a smell.

- Catalogue: https://oops.linkeddata.es/catalogue.jsp · Tool:
  https://oops.linkeddata.es/ · Paper: IJSWIS 10(2), 2014.

**Severity axis:** **Critical** = must fix (breaks consistency / reasoning /
applicability); **Important** = should fix (degrades quality); **Minor** =
cosmetic / best-practice polish.

### Critical (15) — must-fix
- **P01** Polysemous elements
- **P03** Using the relationship "is" instead of `rdfs:subClassOf` / `rdf:type` /
  `owl:sameAs` — *the canonical is-a misuse pitfall*
- **P05** Wrong inverse relationships
- **P06** Cycles in the class hierarchy
- **P14** Misusing `owl:allValuesFrom`
- **P15** Using "some not" in place of "not some"
- **P16** Primitive class used in place of a defined one
- **P19** Multiple domains or ranges in properties
- **P27** Wrong equivalent properties
- **P28** Wrong symmetric relationships
- **P29** Wrong transitive relationships
- **P31** Wrong equivalent classes
- **P37** Ontology not available on the Web
- **P39** Ambiguous namespace
- **P40** Namespace hijacking

### Important (14) — should-fix
- **P10** Missing disjointness
- **P11** Missing domain or range in properties
- **P12** Equivalent properties not explicitly declared
- **P17** Overspecializing a hierarchy
- **P18** Overspecializing the domain or range
- **P23** Duplicating a datatype already in the implementation language
- **P24** Recursive definitions
- **P25** Relationship defined as inverse to itself
- **P26** Inverse relationship defined for a symmetric one
- **P30** Equivalent classes not explicitly declared
- **P34** Untyped class
- **P35** Untyped property
- **P38** No OWL ontology declaration
- **P41** No license declared

### Minor (12) — nice-to-fix
P02 synonyms as classes · P04 unconnected elements · P07 merging different
concepts in one class · P08 missing annotations · P09 missing domain
information · P13 inverse relationships not explicitly declared · P20 misusing
annotations · P21 miscellaneous ("misc/other") class · P22 inconsistent naming
conventions · P32 several classes with the same label · P33 property chain with
one property · P36 URI contains a file extension.

---

## 3. Grüninger & Fox — Competency Questions (TOVE methodology)

Drive design and evaluation from requirements expressed as **competency
questions (CQs)**. Source: Grüninger & Fox, *Methodology for the Design and
Evaluation of Ontologies*, IJCAI-95 Workshop.

- **Motivating scenarios** — informal story problems the ontology must support;
  supply initial informal semantics and motivate *why* the ontology exists.
- **Competency Question (CQ)** — a query the ontology must be able to answer; the
  requirements spec that fixes **scope and expressiveness**. CQs **evaluate**
  commitments, they do not generate them.
- **Informal CQ** — natural language; checks scope and extracts candidate
  terminology (objects, attributes, relations).
- **Formal CQ** — the same question as a first-order-logic **entailment query**
  over the formal terminology. Partitioned into **truth-tests** (must be
  entailed) and **falsity-tests** (must *not* be entailed).

Ordered steps: (1) motivating scenarios → (2) informal CQs → (3) terminology in
FOL → (4) formal CQs → (5) axioms & definitions → (6) completeness theorems.
Steps 3→4→5 iterate: a CQ that can't be expressed or answered forces new
terminology and axioms.

**Judging completeness:** treat the CQ set as an **acceptance test suite**. For
each CQ ask — can the *terminology* even express it, and do the *axioms entail*
the expected answer? A CQ that can't be expressed, or whose answer isn't
entailed, is the work remaining. Complete iff every CQ passes (truth-tests
entailed, falsity-tests correctly refuted).

---

## 4. Gómez-Pérez — evaluation dimensions & taxonomy of errors

A framework for evaluating ontology **content (technical correctness)**. Source:
Gómez-Pérez, *Evaluation of ontologies*, Int. J. Intelligent Systems 16(3), 2001
(origin: 1999 Banff KAW paper).

### Dimensions
- **Consistency** — no individual definition is contradictory, and no
  contradictory conclusion can be **derived** from valid definitions.
- **Completeness** — everything that should be present is stated or **inferable**.
  (You can prove *in*completeness, not full completeness.)
- **Conciseness** — no unnecessary, useless, or **redundant** definitions (stated
  or inferable).
- Plus **Expandability** and **Sensitiveness** (five criteria total).

### Taxonomy of errors in taxonomic knowledge
- **Inconsistency errors**
  - **Circularity errors** — a class is a sub-/super-class of itself; classified
    at **distance 0**, **distance 1**, **distance n**.
  - **Partition errors** — common classes in disjoint decompositions; common
    instances in disjoint decompositions; external instances in exhaustive
    decompositions.
  - **Semantic inconsistency** — classifying a concept as a subclass of one "to
    which it does not really belong" (incorrect semantic classification).
- **Incompleteness errors**
  - **Incomplete concept classification** — domain concepts overlooked.
  - **Disjoint-knowledge omission** — partition declared but the disjointness
    axiom omitted.
  - **Exhaustive-knowledge omission** — decomposition declared but exhaustiveness
    left unspecified.
- **Redundancy errors**
  - **Redundant subclass-of relations** (more than one direct/indirect path).
  - **Redundant instance-of relations** (already implied transitively).
  - **Identical formal definition** of classes (or of instances).

Map onto the dimensions: consistency → circularity / partition / semantic;
completeness → incomplete classification / omitted disjointness / omitted
exhaustiveness; conciseness → redundant edges / identical definitions. Absence of
all error types across all three dimensions = a technically correct taxonomy.

**Attribution caveat:** cite Gómez-Pérez 2001 / 1999 for these categories. Do not
attribute later *extensions* (design anomalies, lonely disjoints, etc.) to her.

---

## Verified sources

- **OntoClean:** Guarino & Welty, *An Overview of OntoClean (v3)* —
  http://www.loa.istc.cnr.it/old/Papers/GuarinoWeltyOntoCleanv3.pdf ·
  https://en.wikipedia.org/wiki/OntoClean · Keet, OntoClean-in-OWL tutorial.
- **OOPS!:** https://oops.linkeddata.es/catalogue.jsp ·
  https://oops.linkeddata.es/ · IJSWIS 2014.
- **Grüninger & Fox:** eil.utoronto.ca …/gruninger-ijcai95.pdf ·
  eil.mie.utoronto.ca/theory/enterprise-modelling/entmethod/ · arXiv 1510.04826.
- **Gómez-Pérez:** *Evaluation of ontologies*, IJIS 16(3), 2001 (Wiley) ·
  *Handbook on Ontologies* ch. "Ontology Evaluation".

The primary OntoClean, Grüninger-Fox 1995, and Gómez-Pérez PDFs are image scans;
their content is corroborated across multiple authoritative sources, but verbatim
quotes should be transcribed from the images directly.
