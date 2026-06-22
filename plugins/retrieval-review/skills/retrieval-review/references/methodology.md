# Retrieval-Review Methodology Reference

The grounding for each review axis: metric definitions, computable formulas,
healthy ranges, technique catalogues, and the constraints a reviewer checks
against. Load this when a finding needs a precise metric, threshold, or citation.

Every formula here is meant to be **run**, not just quoted. Where the embeddings
matrix and a labeled query set are available, compute the number; where they are
not, name it as the metric the user must produce. Sources are listed at the end.

---

## 1. Embedding geometry metrics (axis 3)

The representation's geometry gates every score-based finding downstream. These
are all cheap to compute from the embedding matrix `X ∈ ℝ^{n×d}`.

### Anisotropy (the cone effect)

- **Measure:** mean cosine similarity over random vector pairs (sample a few
  thousand pairs): `aniso = mean_{i≠j} cos(xᵢ, xⱼ)`.
- **Healthy range:** ≈ 0–0.1 (near-isotropic). `> 0.3` = a cone; `> 0.5` =
  severe. Raw transformer upper-layer embeddings reach 0.6–0.99.
- **Why it matters:** in a cone every pair scores high, so a fixed cosine
  relevance threshold measures geometry, not relevance. **Gate this first** — a
  high value invalidates every downstream cosine-threshold and score-fusion
  finding.
- Grounding: Ethayarajh 2019 (the cone effect); Gao 2019 (representation
  degeneration); Mu & Viswanath 2018 (all-but-the-top).

### Alignment & uniformity (Wang & Isola 2020)

Two single-number KPIs computed on **L2-normalized** vectors. Both lower = better.

- **Alignment** (positive pairs should be close):
  `L_align = mean_{(x,y)∈pos} ‖x − y‖²`. Requires known positive pairs (from
  qrels or augmentations).
- **Uniformity** (features should spread over the unit hypersphere):
  `L_uniform = log · mean_{i≠j} exp(−2 ‖xᵢ − xⱼ‖²)`.
- These correlate with downstream retrieval quality (confirmed by SimCSE). Use
  as the headline geometry health pair when positive pairs are available.

### Dimensional collapse — effective rank

- **Measure:** take the singular values `σ₁…σ_d` of `X`, normalize to
  `pᵢ = σᵢ / Σσ`, then `effrank = exp(−Σ pᵢ log pᵢ)` (exponential of the spectrum
  entropy).
- **Read:** `effrank` far below nominal `d` (e.g. ~30 of 768) = the embedding
  lives in a thin subspace; discrimination is lost.
- **Intrinsic dimensionality** (Levina–Bickel MLE, TwoNN / Facco 2017) is
  *diagnostic context* — the data's true manifold dimension — not a fault by
  itself. Distinguish it from effective rank (a collapse signal).
- Grounding: Jing 2021 (dimensional collapse).

### Hubness

- **Measure:** build the k-NN graph; for each point count `N_k(x)` = how many
  queries have `x` among their top-k; compute the **skewness** `S_{N_k}` of that
  distribution.
- **Read:** high positive skew = a few "hub" vectors are nearest-neighbor to
  disproportionately many queries. Invisible per-query, wrecks aggregate recall,
  and is a RAG-poisoning surface.
- **Remedies:** CSLS (cross-domain similarity local scaling), mutual proximity,
  NNN. Grounding: Radovanović 2010; Dinu 2015 (cross-lingual hubness).

### Normalization coherence & metric match

- All vectors unit-norm where cosine/dot is used? Mixed normalized/unnormalized
  vectors silently corrupt ranking.
- Distance metric (cosine / inner-product / L2) must match the model's training
  objective. Cosine on a dot-product-trained model degrades ranking independent
  of index quality.

### The fix ladder (cheapest-sufficient)

1. **L2-normalize** → 2. **mean-center** → 3. **all-but-the-top** (remove the
top few dominant directions, Mu & Viswanath 2018) → 4. **whitening** (BERT-
whitening, Su 2021).

**Caveat — don't cargo-cult whitening:** modern contrastive retrievers
(E5, BGE, GTE) are already near-isotropic; whitening can *hurt* them. Measure
anisotropy first and apply the lightest sufficient step.

### Stability

Re-embedding drift across model/seed versions silently invalidates the index and
any fitted whitening matrix. Treat embedding-version pinning + a re-embed diff as
a CI-grade gate.

### Bias geometry (opt-in, sensitive domains)

WEAT effect size (Caliskan 2017) and the Bolukbasi 2016 direction projection
quantify social bias baked into the geometry. Run only when the domain warrants.

---

## 2. Retrieval / IR evaluation metrics (axis 1)

Definitions for `@k` cutoff metrics over a golden query set with relevance
judgments (qrels).

- **Recall@k** — fraction of all relevant docs that appear in the top-k. The "is
  it even there" sanity check and the ceiling a reranker inherits.
- **Precision@k** — fraction of the top-k that are relevant.
- **nDCG@k** — Discounted Cumulative Gain (graded relevance, log-discounted by
  rank) normalized by the ideal ordering. **The default headline metric** —
  order matters for what the generator sees. Handles graded labels.
- **MRR** — Mean Reciprocal Rank of the first relevant doc. Use only when
  first-hit is all that matters.
- **MAP** — Mean Average Precision; binary relevance only. Do **not** use on
  graded labels.

**Metric-selection rule:** nDCG@k headline; recall@k sanity check; MRR for
first-hit-only; never MAP/binary on graded labels.

**Two evaluation planes:**

- **Retrieval plane** — recall/nDCG/MRR localize *retriever* failures.
- **End-to-end RAG plane** — RAGAS (context precision, context recall,
  faithfulness, answer relevancy) + LLM-as-judge localize *generator* failures.

Single-plane eval can't tell you which layer to fix; a healthy retriever with a
hallucinating generator and a broken retriever both produce wrong answers.

**Golden query set construction:** floor ≈ 50–100 queries; source from real
query logs where possible. LLM-generated query→passage pairs are **"silver"** —
leaky (the generator saw the passage) and recall-inflating; promote to gold via
SME review. Never eval on training queries.

Benchmarks: **BEIR** (Thakur 2021, zero-shot heterogeneous retrieval) and the
**MTEB** retrieval track (Muennighoff 2022) are the standard — but a leaderboard
rank is a candidate filter, not a verdict; re-rank finalists on the domain set.

---

## 3. Rank-fusion catalogue (axis 6)

Combining multiple ranked lists into one.

### Reciprocal Rank Fusion (RRF) — the default

- **Formula:** for document `d`, `RRF(d) = Σ_r 1 / (k + rank_r(d))` summed over
  retrievers `r`; `k ≈ 60` (near-universal default).
- **Why it's the default:** rank-based, so it **ignores raw score scales** and
  sidesteps the cosine-vs-BM25 normalization problem entirely; one parameter,
  hard to misconfigure. Source: Cormack, Clarke & Buettcher 2009.
- **Blind spot:** discards score magnitude — a calibrated, confidently-correct
  retriever is flattened to "rank 1." When scores carry real confidence,
  score-aware fusion can beat it.

### Score-aware fusion (the alternatives)

- **relativeScoreFusion** — normalize each retriever's scores to its own range,
  then weight-combine. Weaviate's default since v1.24 (~6% recall lift over RRF
  in their data).
- **DBSF (distribution-based score fusion)** — normalize by score distribution;
  Qdrant. Warns that top-k outliers skew naive min-max.
- **Weighted sum / convex (alpha)** — `alpha·dense + (1−alpha)·sparse` after
  normalization; requires an eval-backed alpha.
- **CombSUM / CombMNZ** — classic score-sum / sum×(#nonzero) fusion.

**Defaults by system (anchor recommendations to these):** k=60 is near-universal
(Elasticsearch, Milvus, Weaviate rankedFusion); Qdrant defaults to RRF; Weaviate
defaults to relativeScoreFusion; OpenSearch defaults to min-max + arithmetic mean
and **mandates global normalization**.

**Audit rules:** (1) never sum raw cosine + BM25; (2) any non-default weight /
alpha / k must be eval-backed; (3) fusion/prefetch window ≥ final result size
(ideally several×) or recall is starved before fusion sees the candidate; (4)
normalization global + outlier-robust, not per-shard or small-top-k min-max; (5)
require evidence RRF vs score-fusion was *compared* on held-out queries.

**RAG-Fusion** (multi-query expansion + RRF) is orthogonal and composes with
dense+sparse fusion — but audit its N× query cost and constrain reformulations
against intent drift.

---

## 4. Index & ANN reference (axis 4)

### Index families

- **Flat / brute-force** — exact, no recall loss; the ground-truth oracle for
  measuring ANN recall. Viable < ~100K vectors.
- **HNSW** (Malkov & Yashunin 2018) — graph index; in-RAM, excellent recall/
  latency to ~10–100M vectors. Params: `M` (graph degree), `efConstruction`
  (build quality), `efSearch` (runtime recall↔latency dial). Deletes are
  tombstones; build memory ≈ 3–4× IVF.
- **IVF / IVF-PQ** (Jégou 2011 product quantization) — inverted lists + coarse
  quantizer; `nprobe` is the runtime recall dial. Centroids drift → periodic
  retrain; training sample must be representative.
- **DiskANN / Vamana** — on-disk graph for beyond-RAM corpora; streaming
  variants (e.g. pgvectorscale StreamingDiskANN) for high write churn.
- **ScaNN** (Guo 2020) — anisotropic-quantization index.

### Sizing decision tree

Flat < ~100K · HNSW in-RAM to ~10–100M · DiskANN/IVF-PQ beyond RAM or 100M ·
streaming index for high write churn.

### The tradeoff triangle

Recall ↔ latency ↔ memory ↔ build-time. `efSearch`/`nprobe` move recall vs
latency at query time; quantization moves memory vs accuracy. **Demand the
recall/latency curve, not a single benchmark-tuned point.**

### Quantization & rescoring

- Scalar quantization ≈ 75% memory cut; product quantization ≈ 85%; binary
  quantization ≈ 97%.
- **All require a full-precision rescoring + oversampling pass** to recover
  recall. Qdrant reports 76% → 99% recall recovery on a 3072-dim model from
  rescoring alone. Quantization *without* rescoring is a top recall-loss failure.

### Filtered ANN

Unfiltered recall numbers lie when production filters. Low-selectivity
pre-filtering on a whole-corpus HNSW graph can collapse recall; predicate-aware
graphs exist (ACORN, Filtered-DiskANN). Identify pre- vs post- vs in-algorithm
filtering and measure under the real predicate mix.

### Vector-DB defaults (often unintentional)

Weaviate `M=32, efC=128`, dynamic ef · pgvector HNSW `m=16, ef_construction=64` ·
Milvus AUTOINDEX picks for you (verify the actual choice). Distance metric must
match the embedding model.

---

## 5. Retrieval-mode reference (axis 5)

- **Dense** (bi-encoder): DPR (Karpukhin 2020), Contriever, ANCE. Captures
  semantic paraphrase. Quality depends on negative-sampling provenance —
  hard/ANN-mined (ANCE) >> in-batch-only. Out-of-domain recall is a risk
  (BEIR).
- **Sparse / learned-sparse**: BM25 (Robertson & Zaragoza) is the robust
  out-of-domain floor; SPLADE (Formal 2021), uniCOIL, doc2query/DocT5Query add
  learned term expansion. Covers exact match, OOV tokens, rare terms.
- **Hybrid (dense + sparse)** is the safe default — each leg catches what the
  other misses; fuse with RRF (axis 6).
- **Corpus-character → mode fit:** dense-only on ID/SKU/code/entity/jargon
  corpora is the canonical anti-pattern (exact match is the real need).
- **Query transformation:** HyDE (Gao 2022, hypothetical-document embedding),
  multi-query, decomposition, RAG-Fusion — wins in zero-shot/underspecified
  regimes; latency + cost + hallucination overhead on a tuned in-domain hybrid.
- **Vocabulary mismatch** mitigations: doc2query at index time, SPLADE, query
  expansion.

---

## 6. Reranking reference (axis 7)

A precision tool that reorders a candidate set; it **cannot recover a missed
document**, so its ceiling is first-stage recall.

- **Cross-encoders** (monoBERT/monoT5 — Nogueira & Cho 2019, Nogueira 2020;
  Cohere Rerank, BGE-reranker-v2-m3 (Apache-2.0), Jina, Voyage): highest
  precision via full query-doc attention; linear cost in candidates;
  ≈ 50–200ms for top-100, 2–10× retrieval cost. Infeasible over a whole corpus.
- **Late interaction** (ColBERT / ColBERTv2 — Khattab & Zaharia 2020): MaxSim
  over token embeddings; middle ground between bi- and cross-encoders; ColBERTv2
  cut the index ≈ 6–10× vs v1 but still carries a storage/ops tax.
- **LLM listwise** (RankGPT): top quality, seconds-slow, position-biased —
  offline / low-QPS only.

**Audit rules:** (1) prove first-stage recall@k high (≈ ≥ 95% of relevant in the
pool) before crediting the reranker; (2) input ≫ output (retrieve ~50–100 →
return 3–10) or it's a no-op; (3) gate on *measured* nDCG/MRR/recall lift on the
domain set; (4) reranker scores are uncalibrated across models — hard-coded
cutoffs break on model swap; (5) the "90% rule" — ~100 candidates captures most
gain, and under tight latency a small-model-deep beats a large-model-shallow
(inverts as budget loosens); (6) check license/deployment fit (Jina is
restrictive commercially; BGE-reranker is Apache-2.0).

---

## 7. Chunking & data-prep reference (axis 2)

- **Strategies:** fixed-size + overlap · recursive (safe default) · semantic ·
  sentence-window · parent-document / small-to-big.
- **Chunk size:** sweep against the golden set; never pick arbitrarily. Must be
  ≤ the embedding model's context window or the tail is **silently truncated**
  and unretrievable.
- **Boundary-loss fixes (2024):**
  - **Contextual Retrieval** (Anthropic 2024) — prepend an LLM-generated
    chunk-situating context before embedding; reported up to **−67%** retrieval
    failures combined with reranking; pattern retrieve-150 → rerank-20; skip
    retrieval entirely if the whole corpus < ~200K tokens (just put it in
    context).
  - **Late Chunking** (Jina 2024) — embed the whole document, then mean-pool
    per-chunk over the token embeddings; preserves cross-chunk context with no
    LLM call; requires a long-context embedder.
- **Data prep:** dedup near-identical chunks; enrich metadata to enable the
  filtering audited in axis 5.

---

## Verified sources

Geometry:
- Ethayarajh 2019, *How Contextual are Contextualized Word Representations?* —
  https://arxiv.org/abs/1909.00512
- Gao et al. 2019, *Representation Degeneration Problem* —
  https://arxiv.org/abs/1907.12009
- Mu & Viswanath 2018, *All-but-the-Top* — https://arxiv.org/abs/1702.01417
- Wang & Isola 2020, *Alignment and Uniformity on the Hypersphere* —
  https://arxiv.org/abs/2005.10242
- Jing et al. 2021, *Dimensional Collapse* — https://arxiv.org/abs/2110.09348
- Radovanović et al. 2010, *Hubs in Space* —
  https://www.jmlr.org/papers/v11/radovanovic10a.html
- Su et al. 2021, *Whitening Sentence Representations* —
  https://arxiv.org/abs/2103.15316
- Caliskan et al. 2017, *Semantics derived automatically … (WEAT)* — Science 356.
- Facco et al. 2017, *Intrinsic dimension (TwoNN)* —
  https://www.nature.com/articles/s41598-017-11873-y

Evaluation:
- Thakur et al. 2021, *BEIR* — https://arxiv.org/abs/2104.08663
- Muennighoff et al. 2022, *MTEB* — https://arxiv.org/abs/2210.07316
- RAGAS — Es et al. 2023, https://arxiv.org/abs/2309.15217

Fusion:
- Cormack, Clarke & Buettcher 2009, *Reciprocal Rank Fusion* —
  https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf
- Weaviate hybrid/fusion docs · Qdrant DBSF docs · OpenSearch hybrid-search docs.

Index / ANN:
- Malkov & Yashunin 2018, *HNSW* — https://arxiv.org/abs/1603.09320
- Jégou et al. 2011, *Product Quantization* —
  https://ieeexplore.ieee.org/document/5432202
- Guo et al. 2020, *ScaNN* — https://arxiv.org/abs/1908.10396

Retrieval / rerank / chunking:
- Karpukhin et al. 2020, *DPR* — https://arxiv.org/abs/2004.04906
- Formal et al. 2021, *SPLADE* — https://arxiv.org/abs/2107.05720
- Gao et al. 2022, *HyDE* — https://arxiv.org/abs/2212.10496
- Nogueira et al. 2020, *Document Ranking with T5 (monoT5)* —
  https://arxiv.org/abs/2003.06713
- Khattab & Zaharia 2020, *ColBERT* — https://arxiv.org/abs/2004.12832
- Anthropic 2024, *Introducing Contextual Retrieval* —
  https://www.anthropic.com/news/contextual-retrieval
- Jina AI 2024, *Late Chunking* — https://arxiv.org/abs/2409.04701

Raw per-axis research digests (with extended notes) are persisted under
`~/dev/work/dawks/spaces/ClaudeTooling/retrieval-skill/research/`.
