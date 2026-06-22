---
name: retrieval-review
description: Use when reviewing or auditing a retrieval / vector-index / RAG pipeline for quality before it silently feeds wrong or missing context to a generator. Triggers — /retrieval-review, 'review my RAG pipeline', 'audit this vector index', 'why is retrieval bad', 'check my hybrid search', 'review my embeddings retrieval', 'is my RRF/reranker configured right', 'audit my vector DB setup'. Runs a structured seven-axis review (eval foundation, corpus & chunking, embedding geometry, index & ANN fidelity, retrieval composition, rank fusion, reranking) in a fixed load-bearing order, grounded in BEIR/MTEB evaluation methodology, the anisotropy & alignment/uniformity geometry literature, ANN-index recall theory, and the rank-fusion (RRF) and cross-encoder reranking research. Produces a severity-ranked findings list led by the issues that make the right document structurally unretrievable — each with the smell, the offending layer, why it's a problem, the metric that proves it, and a concrete fix.
---

# Retrieval Review

## Overview

Audit a retrieval / vector-index pipeline for quality and flag the defects that
make it return wrong or missing context — *before* that context reaches the
generator and gets confidently rephrased into a wrong answer. The review runs
across seven axes in a fixed order, because earlier axes are the substrate the
later ones are measured and interpreted against (you cannot trust a cosine
threshold until you've checked the geometry; you cannot credit a reranker until
you've measured first-stage recall). Output is a prioritized findings list, led
by the issues that make a relevant document **structurally unretrievable** — the
retrieval analog of a system asserting a false fact.

This is the *audit* twin of a constructive `/retrieval-draft` (designing a
pipeline from scratch), the way `/ontology-review` pairs with `/ontology-draft`.

**This review is numeric, not config-only.** Retrieval quality is a measured
property. Where the embeddings and a labeled query set are available, *compute*
the metrics (recall@k, anisotropy, effective rank, fusion-window coverage);
where they are not, name the exact metric the user must run. A review that only
reads configuration is guessing.

## Quick Reference

| # | Axis | Catches | Grounding |
|---|------|---------|-----------|
| 1 | **Eval foundation** | No golden query set / qrels; eval on training queries; wrong metric for the labels; single-plane eval; synthetic-only "silver" labels trusted as gold | BEIR, MTEB, RAGAS; the retrieval analog of competency questions |
| 2 | **Corpus & chunking** | Arbitrary chunk size never swept; chunk exceeds embedding context (silent truncation); boundary semantic loss with no contextualization; no dedup | Contextual Retrieval (Anthropic 2024), Late Chunking (Jina 2024) |
| 3 | **Embedding geometry** | Anisotropy / cone effect inflating cosine; dimensional collapse; hubness; mixed normalized/unnormalized; metric ≠ training objective | Ethayarajh 2019, Wang & Isola 2020, Radovanović 2010, Mu & Viswanath 2018 |
| 4 | **Index & ANN fidelity** | Recall never measured vs brute force; untuned ef/nprobe; quantization without rescoring; recall measured unfiltered when prod filters; distance-metric mismatch | HNSW (Malkov 2018), IVF-PQ (Jégou 2011), BEIR recall methodology |
| 5 | **Retrieval composition** | Dense-only on exact-match corpora; no sparse leg; dense out-of-domain unvalidated; filter strategy that kills recall; query-transform over/under-use | DPR, BM25, SPLADE, BEIR, HyDE 2022 |
| 6 | **Rank fusion** | Summing raw cosine + BM25 (score-scale mismatch); non-default weight/k with no eval; fusion window too narrow; unstable normalization | RRF (Cormack 2009), relativeScoreFusion, DBSF |
| 7 | **Reranking** | No first-stage recall headroom; input ≈ output (no-op); lift never eval-gated; hard-coded uncalibrated score cutoff; latency budget ignored | monoT5 (Nogueira 2020), ColBERTv2 (Khattab 2020) |

Deep detail — metric formulas, healthy ranges, the fusion catalogue, ANN sizing
guidance, and the source list — lives in `references/methodology.md`. Load it
when a finding needs a precise metric, threshold, or citation.

## Inputs

Accept the pipeline in whatever form it exists: a running RAG codebase, a vector
DB configuration (Qdrant / Milvus / Weaviate / pgvector / Elasticsearch / Vespa
/ FAISS), an embeddings matrix plus a query set, a retrieval-config block, or a
prose description of the stack. To run the full audit you need, at minimum: the
**embedding model**, the **index type and parameters**, the **retrieval / fusion
/ rerank configuration**, the **corpus character** (what kind of text, what
queries), and — critically — a **labeled query set**. If no eval set exists, that
*is* finding #1 (see axis 1); offer to help bootstrap one before proceeding, but
still run the structural axes.

If the target or scope is ambiguous (which corpus, which index, which retrieval
path), ask before starting — do not guess the scope of a measurement-driven
audit.

For a large audit the seven axes may be delegated one per sub-agent to keep the
main context lean; each delegated reviewer must receive the **full stack
description and access to the measurements**, not a single config slice — the
axes are interdependent.

## The Review (run the axes in order)

### 1. Eval foundation — is the pipeline even observable?

Retrieval quality is a *measured* property; without a labeled query set the rest
of the audit can only inspect configuration, never behavior. This is the
retrieval analog of competency questions, and it comes **first** because
measurement is the whole game.

- **Golden query set + qrels:** is there a set of representative queries with
  judged relevant documents (qrels)? Floor ≈ 50–100 queries; sourced from real
  query logs where possible, LLM-generated query→passage pairs promoted by SME
  review otherwise. **No labeled set = Critical**: the pipeline is unobservable
  and every downstream "is the right doc retrieved" finding is unprovable.
- **Don't trust synthetic as gold:** LLM-generated eval is *silver* — leaky
  labels (the generator saw the passage) inflate recall. Flag synthetic-only
  eval used as ground truth.
- **Right metric for the labels:** `nDCG@k` is the default headline (order
  matters for what the generator sees); `recall@k` is the "is it even there"
  sanity check; `MRR` only when first-hit is all that matters; never `MAP` or
  binary metrics on graded labels. (Definitions in `references/methodology.md`.)
- **Two planes, both needed:** retrieval metrics (recall/nDCG/MRR) localize
  *retriever* failures; end-to-end RAG metrics (RAGAS context precision/recall,
  faithfulness) localize *generator* failures. Single-plane eval can't tell you
  which layer to fix.
- **No eval on training queries** — leakage inflates every number.

### 2. Corpus & chunking — what actually got indexed?

You can only retrieve what you embedded. Audit the units in the index.

- **Chunk size swept, not guessed:** chunk size must be tuned against the golden
  set (axis 1), not picked arbitrarily. Recursive splitting with overlap is the
  safe default.
- **Chunk ≤ embedding context window:** a chunk longer than the model's max input
  is **silently truncated** — the tail is never embedded and never retrievable.
  A real, common, invisible bug. Flag any chunk-size / model-context mismatch.
- **Boundary semantic loss:** naive fixed-size splits sever context across chunk
  boundaries. Check for a mitigation where the corpus warrants it — **Contextual
  Retrieval** (LLM-prepended chunk context; reported up to −67% retrieval
  failures with reranking) or **Late Chunking** (embed the whole doc, then pool
  per-chunk; needs a long-context embedder).
- **Dedup & metadata:** near-duplicate chunks crowd out diverse results; missing
  metadata blocks the filtering audited in axis 5.

### 3. Embedding geometry — is the representation healthy?

The representation's geometry **gates every score-based finding downstream**. An
anisotropic space inflates all cosine similarities, so any fixed cosine
threshold, score-aware fusion (axis 6), or reranker cutoff (axis 7) is invalid
until this axis passes. Run it before interpreting any score. (Formulas and
healthy ranges in `references/methodology.md`.)

- **Anisotropy / cone effect:** mean cosine of random pairs. Healthy ≈ 0–0.1;
  > 0.3 is a cone; > 0.5 is severe (raw transformer upper layers hit 0.6–0.99).
  **A high value invalidates every downstream cosine-threshold finding** — gate
  on it first. Fixed cosine cutoffs with no isotropy check are a smell.
- **Alignment & uniformity (Wang & Isola):** two single-number KPIs on
  normalized vectors — alignment (positives should be close) and uniformity
  (the space should spread over the hypersphere). Both lower = better; they are
  the headline geometry health metrics.
- **Dimensional collapse:** effective rank (entropy of the normalized singular-
  value spectrum) far below the nominal dimension means the embedding occupies a
  thin subspace — discrimination is lost. (Intrinsic dimensionality is
  diagnostic context, not a fault on its own.)
- **Hubness:** a few vectors that are nearest-neighbor to disproportionately many
  queries (skew of the k-occurrence distribution). Invisible per-query, wrecks
  aggregate recall, and is a RAG poisoning surface. Remedies: CSLS, mutual
  proximity.
- **Normalization coherence & metric match:** all vectors unit-norm? Distance
  metric (cosine / dot / L2) matching how the model was trained? Mixed
  normalized/unnormalized vectors, or cosine on a dot-trained model, silently
  tank ranking — high-impact, trivially detectable.
- **Re-embedding stability:** re-embedding drift across model/seed versions
  silently invalidates the index and any fitted whitening matrix — a CI-grade
  gate. **Fix ladder, cheapest-sufficient:** L2-normalize → mean-center →
  all-but-the-top → whitening. Don't cargo-cult whitening: modern contrastive
  retrievers (E5/BGE/GTE) are already near-isotropic and whitening can *hurt*
  them.

### 4. Index & ANN fidelity — is it finding what's in the index?

The cardinal measurement of the whole audit: **measured recall@k against an
exact / brute-force ground truth.** An ANN index is an approximation; its recall
is unknown until measured, and it is the ceiling everything above it inherits.

- **Recall vs brute force is non-negotiable:** compute recall@k against a flat /
  exact search on a representative query set. **No recall measurement = Critical
  ("cardinal sin"):** every tuning question above is unanswerable.
- **Index fit by scale/RAM:** flat < ~100K vectors; HNSW in-RAM up to ~10–100M;
  DiskANN / IVF-PQ beyond RAM; streaming index for high write churn. Brute force
  at scale, or HNSW when memory can't hold the graph, is a misfit.
- **Runtime recall dials:** `efSearch` (HNSW) / `nprobe` (IVF) trade recall vs
  latency — demand the *curve*, not a single default point.
- **Quantization needs rescoring:** scalar/product/binary quantization (≈75–97%
  memory cut) all require a full-precision rescoring + oversampling pass;
  quantization without rescoring is a top recall-loss failure mode.
- **Filtered recall is a separate, brutal variable:** unfiltered recall numbers
  *lie* when production always applies a metadata filter. Low-selectivity
  pre-filtering on a whole-corpus HNSW graph can collapse recall. Measure under
  the real predicate mix; identify pre- vs post- vs in-algorithm filtering.
- **Distance-metric mismatch & operational drift:** metric must match the model
  (see axis 3); HNSW deletes are tombstones and IVF centroids drift — a
  rebuild/retrain plan must exist.

### 5. Retrieval composition — dense, sparse, hybrid, transforms

Does the retrieval strategy fit the corpus character? Mismatch here makes the
right document unretrievable no matter how good the index.

- **Corpus-character → mode fit (the #1 finding):** dense-only on ID / SKU /
  code / entity / jargon-heavy corpora is the canonical anti-pattern — the user's
  real need is *exact match*, which a paraphrase-tuned embedding will miss.
  **Critical: recommend hybrid (dense + sparse).**
- **Confirm a sparse leg exists:** BM25 / learned-sparse (SPLADE) covers exact
  match, out-of-vocabulary tokens, rare terms, and out-of-domain queries — BEIR
  shows BM25 is the robust floor that dense retrievers often underperform
  zero-shot.
- **Dense out-of-domain = unvalidated recall risk:** is the embedding model's
  training distribution matched to this corpus, with *measured* recall (not an
  MTEB leaderboard rank)? Never trust a benchmark rank as a verdict — re-rank
  candidate models on the domain set.
- **Filter strategy vs ANN recall:** post-filter-without-over-fetch and missing
  pre-filter are top "the right doc is never returned" causes (cross-reference
  axis 4's filtered-recall check).
- **Query transformation cost/benefit:** HyDE / multi-query / decomposition pay
  off in zero-shot or underspecified regimes but add latency, cost, and
  hallucination risk on a tuned in-domain hybrid. Flag both over- and under-use.

### 6. Rank fusion — combine rankings without corrupting them

When multiple retrievers feed one result list, how they merge is a common silent
defect. (Fusion catalogue and defaults by DB in `references/methodology.md`.)

- **Score-scale safety (the #1 fusion bug):** flag any path that **sums raw
  cosine + BM25** without normalization — the scales are incomparable.
  Reciprocal Rank Fusion (RRF, `1/(k+rank)`, k ≈ 60) is the tuning-free default
  that sidesteps it by using ranks, not scores.
- **RRF discards magnitude — know its blind spot:** when one retriever is
  *calibrated and confidently correct*, RRF flattens it to "just rank 1," and
  score-aware fusion (relativeScoreFusion, DBSF, weighted sum) can win. Neither
  dominates universally — require evidence the two were *compared* on held-out
  queries, not chosen by default.
- **Any non-default weight / alpha / k must be eval-backed:** hand-tuned fusion
  with no measurement is a common production anti-pattern — treat it as a
  finding.
- **Fusion window must be wide enough:** the per-retriever prefetch / candidate
  window (`rank_window_size`) must be ≥ the final result size, ideally several×;
  too narrow starves recall before fusion ever sees the candidate.
- **Normalization must be global + outlier-robust:** per-shard or small-top-k
  min-max is unstable; prefer distribution-based normalization for skewed scores.

### 7. Reranking — a precision tool bounded by first-stage recall

Reranking can only reorder what was already retrieved; it **never recovers a
missed document.** Its value is entirely capped by the recall measured in axes
4–5.

- **First-stage recall is the hard ceiling (check first):** prove first-stage
  recall@k is high (target ≈ ≥ 95% of relevant in the candidate pool) *before*
  crediting any reranker. A reranker over a low-recall first stage is reordering
  garbage.
- **Headroom — input must be ≫ output:** retrieve ~50–100 → return 3–10. If the
  reranker's input ≈ its output, it is a **no-op** doing nothing but adding
  latency — auto-flag.
- **Eval-gated lift:** gate every reranker on *measured* nDCG/MRR/recall lift on
  the domain set. Reranker scores are not calibrated across models, so any
  **hard-coded score cutoff breaks silently on a model swap** — flag fixed
  cutoffs.
- **Model class fits the budget:** cross-encoder (highest precision, linear
  cost), late interaction / ColBERTv2 (middle ground, storage tax), or LLM
  listwise (top quality, seconds-slow, position-biased, offline/low-QPS only).
  Cross-encoding a whole corpus is infeasible — it only reranks a candidate set.
- **Latency & deployment:** ~50–200ms for a top-100 cross-encoder, 2–10× the
  retrieval cost; check the latency budget and any license/deployment mismatch.

## Output

Produce a **prioritized, severity-ranked findings list** — no praise padding, no
restating what is fine at length. Lead with the issues that make a relevant
document structurally unretrievable or the pipeline unmeasurable.

Severity: **Critical** (the right document is structurally unretrievable, the
pipeline is unmeasurable, or geometry invalidates every score) → **Important**
(degrades recall/precision but not structurally fatal) → **Minor** (hygiene,
defaults left untuned without demonstrated harm, missing annotations). Rank
within severity by blast radius.

Each finding uses this structure:

```
### [SEVERITY] <short finding title>
- **Smell:** <the pattern, named — e.g. "raw-score fusion", "anisotropic-cosine", "no recall headroom", "silent chunk truncation">
- **Where:** <the specific layer / component / config value — name it exactly>
- **Why it's a problem:** <the concrete consequence; for Critical, the query that silently returns wrong or missing context>
- **Fix:** <a specific, actionable correction — the metric to run, the sparse leg to add, the rescoring pass to enable>
- **Grounding:** <the metric that proves it + source — e.g. "recall@20 unmeasured (BEIR)", "anisotropy ≈ 0.4 > 0.3 (Ethayarajh 2019)", "input k = output k → no-op">
```

Close with a one-line **verdict** (e.g. "2 Critical, 4 Important — retrieval is
unmeasurable and dense-only on a code corpus; not trustworthy until an eval set
and a sparse leg exist") and, if useful, the single highest-leverage fix.

## Common Mistakes

### ❌ Auditing configuration instead of measuring behavior

**Problem:** Declaring the pipeline "fine" from reading the config — embedding
model, index params, RRF settings — without ever computing recall@k.

**Why it's wrong:** Retrieval quality is a measured property. A perfectly
reasonable-looking config can have 40% recall because of an untuned `efSearch`, a
truncated chunk, or a filter collapse. Config is a hypothesis; the metric is the
evidence.

**Fix:** Run axis 1 first. If there's no eval set, that's finding #1 — bootstrap
one before crediting anything else.

### ❌ Reading cosine thresholds without an isotropy check

**Problem:** Trusting a "similarity > 0.8 = relevant" cutoff, or tuning
score-aware fusion, on an anisotropic space.

**Why it's wrong:** In a cone, *every* pair scores high — the threshold is
measuring the geometry, not relevance. Every score-based finding downstream is
invalid until axis 3 passes.

**Fix:** Measure anisotropy (mean random-pair cosine) before interpreting any
score. Gate axes 6–7 on it.

### ❌ Crediting a reranker with no first-stage recall headroom

**Problem:** Adding a cross-encoder reranker to "fix" bad results when the first
stage already missed the relevant document.

**Why it's wrong:** A reranker only reorders the candidate pool — it cannot
retrieve what was never there. Reranking a low-recall first stage reorders
garbage.

**Fix:** Measure first-stage recall@k first; widen retrieval / add a sparse leg
until the relevant docs are in the pool, *then* rerank.

### ❌ Summing raw cosine and BM25 scores

**Problem:** Fusing dense and sparse results by adding their raw scores.

**Why it's wrong:** Cosine (~0–1) and BM25 (unbounded) are on incomparable
scales — the sum is dominated by whichever scale is larger, not by relevance.

**Fix:** Use RRF (`1/(k+rank)`, k ≈ 60) which fuses ranks, or normalize globally
before a score-aware fusion — and prove the choice on held-out queries.

### ❌ Trusting an MTEB/leaderboard rank as a verdict

**Problem:** Picking the embedding or reranker model by its benchmark ranking and
calling retrieval done.

**Why it's wrong:** BEIR shows models that top a benchmark often underperform
out-of-domain; your corpus is not the benchmark.

**Fix:** Treat the leaderboard as a candidate filter; re-rank the finalists on
*your* golden set with *your* metric.

### ❌ Measuring unfiltered recall when production always filters

**Problem:** Reporting a healthy recall@10 measured with no metadata filter, when
every production query applies one.

**Why it's wrong:** Low-selectivity pre-filtering on an HNSW graph can collapse
recall; the unfiltered number is fiction.

**Fix:** Measure recall under the real production predicate mix.

## Notes

- The review is **read-only and advisory** — it produces findings and fixes, it
  does not mutate the pipeline. Apply fixes as a separate, confirmed step.
- The review is **numeric**: where embeddings and a labeled query set exist,
  compute the metrics; where they don't, name the exact metric to run. Don't
  ship a verdict built only on configuration inspection.
- **Axis order is load-bearing.** Axis 1 (eval) is the measurement substrate for
  axes 4–7; axis 3 (geometry) gates score interpretation in axes 6–7; axis 4
  (recall) is the ceiling that bounds axis 7. Do not reorder.
- This skill **audits**; a future `/retrieval-draft` would **construct** (design
  chunking, model, index, fusion, and rerank choices for a corpus from scratch) —
  the same draft↔review pairing as `/ontology-draft` ↔ `/ontology-review`.
- It is distinct from `/aio` (which audits whole agentic systems broadly): this
  goes deep on the *retrieval subsystem* — fusion math, ANN recall, geometry,
  eval harness — the way `/schema-review` is distinct from a general code review.
- The metric formulas, healthy ranges, fusion catalogue, ANN sizing guidance, and
  source citations are the shared vocabulary — cite them in findings so they are
  checkable. Full detail in `references/methodology.md`.
