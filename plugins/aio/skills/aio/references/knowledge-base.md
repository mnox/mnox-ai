# AIO Knowledge Base — Evidence Layer

This is the **on-demand evidence layer** for the `aio` skill. The core `SKILL.md` carries the
operational *rules*; this file carries the *proof*. Core skill text points here with `[KB:claim-id]`
tags — resolve a tag by jumping to its `### [KB:claim-id]` anchor below.

**Claim-centric, consolidation-managed.** Sources are grouped under the operational claim they
support, not listed chronologically. `/aio-update` maintains this file deterministically: a new
finding **updates a claim's `**Evidence**` headline** and **demotes the prior source to `**Trail**`** —
it does NOT append a new bullet. The full append-only citation history lives in the dawks sources
registry, not here; this file holds only the current headline + a compressed supersession trail.

**How to read an entry:**
- **Rule** — the one-line imperative the evidence backs (what the agent should DO).
- **Evidence** — current best source(s), strongest/newest first. Format: *Name (venue/arxiv, date): one-clause finding.* This is the headline citation.
- **Trail** — superseded/prior sources, one compressed line each, prefixed with the reason (`superseded by X:` / `earlier:`). Omitted when there's no trail.

Reference tables (frameworks, eval-tools, guardrail-tools) and the cost-strategies list are
reference data, not citation chains — they carry only a **Rule** + the table/list.

---

## Architecture

### [KB:pattern-hierarchy] Start with the simplest pattern that works
**Rule:** Default to the simplest orchestration pattern; justify every step up the complexity ladder, and never reach for multi-agent by default.
**Evidence:** Single-vs-multi-agent (arxiv 2604.02460, Apr 2026): single agents match or beat multi-agent systems at normalized compute — handoffs lose information (Data Processing Inequality); multi-agent only wins with heterogeneous models or structured adversarial debate. AgentArch (arxiv 2509.10769, ServiceNow): 18 configs × 6 LLMs, best only 35.3% on complex enterprise tasks, no universally optimal architecture — benchmark your specific use case. "Building Effective Agents" (Anthropic, Dec 2024): canonical pattern hierarchy (single+retrieval → prompt chaining → routing → parallelization → orchestrator-workers → evaluator-optimizer → full agent loop), start simple.
**Trail:** when MAS wins it's topology not headcount — LATTE (arxiv 2605.06320, May 2026): agent-maintained shared coordination graph beats static MAS at 47.5% tokens, 79.7% vs 33.9% (MetaGPT) acc, ~10× fewer write conflicts.

### [KB:harness-design] The harness, not the weights, is the optimization surface
**Rule:** Treat agent quality as harness quality — two-phase init, feature-list JSON state, distributed sub-agent output, registry-style tools over MCP/plugin where production-proven.
**Evidence:** Life-Harness (arxiv 2605.22166, May 2026): evolving the runtime interface (env contracts, procedural skills, action realization, trajectory regulation) of *frozen* LLMs yields 88.5% avg relative improvement across 126 settings, transferring across 17 backbones. Dive into Claude Code (arxiv 2604.14228, Apr 2026): 98.4% of LOC is harness/infra — five compaction strategies, seven safety layers, four extension surfaces. Architectural Design Decisions in Harnesses (arxiv 2604.18071, Apr 2026): empirical 5-pattern taxonomy; file-persistent/hybrid/hierarchical context dominates and registry-style tools still beat MCP/plugin in production. "Effective Harnesses for Long-Running Agents" (Anthropic Engineering, 2025): two-phase init, feature-list JSON, distributed output.

### [KB:tool-design] Treat tool specs as contracts
**Rule:** Action-verb spec openings, explicit typed params with units, few-shot examples, semantic field names (`name`/`image_url` not `uuid`/`mime_type`), rationale-before-call, pagination/truncation, consolidate over proliferate.
**Evidence:** "Writing Effective Tools for AI Agents" (Anthropic Engineering, 2025): tool descriptions are as load-bearing as the system prompt; rationale-before-call dramatically reduces hallucinated calls; expose `ResponseFormat` for concise-vs-detailed.

> Tool-execution security (sandboxing tool surfaces as untrusted RPC) is defined at **[KB:tool-exec-sandbox]** under Safety & Guardrails — it belongs to architecture too.

### [KB:context-eng] Provision context just-in-time, not front-loaded
**Rule:** Isolate detail in sub-agents that return condensed summaries (1–2k tokens); compact near context limits; use structured scratchpad memory layers; evolve context as a playbook.
**Evidence:** ACE — Agentic Context Engineering (arxiv 2510.04618, ICLR 2026): contexts as evolving playbooks via Generator/Reflector/Curator roles, prevents brevity bias and context collapse, +10.6% on agent benchmarks. "Effective Context Engineering for AI Agents" (Anthropic Engineering, 2025): sub-agent isolation, compaction, structured memory over raw conversation stuffing.

### [KB:progressive-disclosure] Disclose context progressively — measure the sign before injecting
**Rule:** Surface a thin high-signal core by default; let the agent *fetch* deeper detail on demand. More context is not more capability — run a context-free diagnostic trial before adding any context channel.
**Evidence:** When Context Hurts (arxiv 2605.04361, May 2026): identical context yields up to 20× gains OR 46% degradation across 2,700+ MAS trajectories; baseline no-context performance predicts the sign at r=-0.82 — one cheap context-free trial forecasts whether injection helps or hurts. Context Length Alone Hurts (arxiv 2510.05381): performance degrades 13.9–85% as context length grows even with perfect retrieval and irrelevant tokens replaced by whitespace. Anthropic Agent Skills + "Effective Context Engineering" guidance: layered always-loaded core + on-demand references is the prescribed default.

---

## Memory

### [KB:memory-justify] Don't add memory by default
**Rule:** Require explicit justification before adding a memory system — a workload that demonstrably needs cross-session recall, multi-hop relational reasoning, or context exceeding long-context capacity. Otherwise long-context is the simpler, better answer.
**Evidence:** AMA-Bench (arxiv 2602.22769, Feb 2026): plain long-context baselines often beat dedicated memory systems across 6 agent task families, with high cross-task variance among memory architectures.
**Trail:** backend-selection reference — vector stores (semantic retrieval), KV (speed-critical), knowledge graphs (relational/traceable), git checkpointing (rollback).

### [KB:memory-helps] Well-architected memory improves outcomes
**Rule:** Persistent text/episodic memory with reflection + recency/importance/relevance-scored retrieval measurably lifts agent performance — no gradient updates required.
**Evidence:** Mem0 (arxiv 2504.19413, 2025): +26% over OpenAI baseline on LOCOMO, 91% lower p95 latency, 90%+ token savings; graph-augmented adds ~2%. Reflexion (arxiv 2303.11366, Shinn et al., NeurIPS 2023): natural-language self-critiques in episodic memory give +11% HumanEval, +22% AlfWorld, +20% HotPotQA. Generative Agents (arxiv 2304.03442, Park et al., UIST 2023, Stanford/Google): memory stream + reflection synthesis + recency/importance/relevance retrieval; ablating reflection or retrieval degrades behavioral coherence.

### [KB:memory-harms] Naive memory is actively harmful
**Rule:** Never use flat similarity-only retrieval without correction/deletion — high similarity to stored memory causes blind replication and error propagation; bloat degrades performance even with perfect retrieval; retrieval accuracy alone doesn't stop hallucination.
**Evidence:** Experience-Following (arxiv 2505.16067, Xu et al., 2025): high memory similarity causes blind replication of past output and error propagation from wrong memories; utility-based deletion yields +10% over naive. Context Length Alone Hurts (arxiv 2510.05381): degradation 13.9–85% as context grows, even with perfect retrieval. ReDeEP (arxiv 2410.11414, ICLR 2025): RAG hallucinates even with accurate retrieval because parametric knowledge overrides external context in the residual stream — retrieval accuracy is insufficient.

### [KB:memory-patterns] Use tiered, structured memory — not flat vector stores
**Rule:** Prefer OS-style tiered memory (avoids context bloat) and structured/linked organization (enables multi-hop) over flat retrieval; score retrieval beyond naive similarity; include correction/deletion.
**Evidence:** A-MEM (arxiv 2502.12110, Xu et al., 2025): Zettelkasten-style structured memory with dynamic indexing and cross-linking outperforms flat retrieval stores. MemGPT (arxiv 2310.08560, Packer et al., 2023, UC Berkeley): OS-inspired virtual context management, tiered main+disk memory enables beyond-context-window operation. Graph-based Agent Memory survey (arxiv 2602.05665): graph retrieval (relationship traversal) enables multi-hop reasoning flat vector stores miss; open problems — identity resolution, staleness detection. Memory for Autonomous LLM Agents survey (arxiv 2603.07670): temporal-scope × representational-substrate × control-policy taxonomy; move eval from static recall to multi-session agentic tests.

### [KB:memory-security] Memory needs a security model, not just a recall model
**Rule:** For long-term memory, the first question is governance — who writes, who reads, what the agent can unlearn — not "vector or graph." For regulated workflows prefer immutable append-only logs over editable memory.
**Evidence:** Mnemonic Sovereignty (arxiv 2604.16548, Apr 2026): six-phase memory lifecycle (Write/Store/Retrieve/Execute/Share/Forget) × four security objectives; zero existing architectures implement all nine governance primitives; confidentiality/availability/forget attacks sparsely studied. DPM Stateless Decision Memory (arxiv 2604.20158, Apr 2026): append-only event log + single task-conditioned projection (facts/reasoning/compliance within a bounded budget) — auditable, cheap, nothing silently mutated; production pattern for finance/healthcare. MAGE Shadow Memory (arxiv 2605.03228, May 2026): parallel security-critical memory channel preserving trajectory integrity against poisoning/drift during continual learning.

### [KB:agentic-rag] Sub-query decomposition is the highest-leverage agentic-RAG component
**Rule:** Expose hierarchical retrieval tools (keyword/semantic search, chunk read) directly to the agent and prioritize sub-query decomposition; add process-level (not outcome-only) reward when training RAG agents.
**Evidence:** SoK: Agentic RAG (arxiv 2603.07379, Mar 2026): field-defining systematization — unified taxonomy across architectures/eval/research directions; inconsistent evaluation is the single biggest blocker; spine document for any 2026 agentic-RAG project. ProRAG (arxiv 2601.21912): step-level process rewards via MCTS-based PRM attack reward sparsity and process hallucinations, SOTA on 5 multi-hop benchmarks over outcome-RL. A-RAG (arxiv 2602.03442, Feb 2026): hierarchical retrieval tools exposed to the agent; sub-query decomposition is the single most impactful component — more than reranking or iterative retrieval alone.

---

## Reliability

### [KB:reliability-lags-capability] Reliability lags capability — scaling alone is insufficient
**Rule:** Don't assume a more capable model is deployment-ready; engineer reliability explicitly.
**Evidence:** Towards a Science of AI Agent Reliability (arxiv 2602.16666, Feb 2026): reliability gains lag noticeably behind capability progress; scaling model capability alone is insufficient for deployment readiness.

### [KB:three-layer-testing] Test in three layers — unit, eval, integration
**Rule:** Layer 1 mock-LLM unit tests (tool routing, arg extraction, schema validation) in CI on every commit; Layer 2 evals on curated datasets with LLM-as-judge + threshold assertions, prompts versioned and regression-gated; Layer 3 integration/E2E against real or simulated environments covering timeouts, auth failures, bad responses, edge cases.
**Evidence:** "Demystifying Evals for AI Agents" (Anthropic Engineering): start with 20–50 real-failure tasks, map eval types (automated/monitoring/A-B/transcript) to deployment stage, CI-gate automated evals on every model/prompt change. Eval adoption gap (LangChain State of Agent Engineering): only 52% run offline evals, 37% online — most teams fly blind. Tooling: llmock (CopilotKit) deterministic mock LLM; persona simulation (Maxim AI, LangWatch Scenario) for Layer 3.

### [KB:reliability-decay] Measure reliability decay, not pass@1
**Rule:** For agents running beyond a handful of steps, replace single-shot success with reliability-decay metrics over horizon length, plus checkpoint-and-restart for meltdown runs.
**Evidence:** Beyond pass@1 (arxiv 2603.29231, Mar 2026): reliability-decay metrics (RDC, VAF, GDS) measure horizon degradation; MOP-entropy-triggered checkpoint-and-restart recovers ~19% of meltdown runs.

### [KB:failure-attribution] Run a failure-attribution loop that recognizes drift, not just terminal failure
**Rule:** For any agent running >10 steps, pair an online attribution loop with offline failure-rich training; instrument trajectory drift (compounding off-path tool calls), not just terminal failures. Attribution is now cheap enough to run in the loop.
**Evidence:** ErrorProbe (arxiv 2604.17658, Apr 2026): anomaly-detection → backward-trace → hypothesis-validation (Strategist/Investigator/Arbiter) with episodic memory updated only on executable evidence — upgrade beyond AgentDebug. HORIZON (arxiv 2604.11978, Apr 2026): 3,100+ trajectories show agents collapse via compounding off-path tool calls, not single hard steps; LLM-as-judge attribution κ=0.84. MASPrism (arxiv 2605.07509, May 2026): attributes from prefill signals (token-NLL + attention) with no decoding, ~6.7× faster than replay. Conformal Agent Error Attribution (arxiv 2605.06788, May 2026): conformal prediction sets with finite-sample, distribution-free coverage guarantees.
**Trail:** earlier online loop — AgentDebug (ICLR 2026, openreview PFR4E8583W): root-cause isolation feeding corrective signals back, up to +26% relative success across ALFWorld/GAIA/WebShop. earlier offline complement — PALADIN (arxiv 2509.25238, ICLR 2026): failure-rich trajectory training (timeouts, malformed outputs, silent failures) for diagnosis/replanning/recovery.

### [KB:diagnosis-recovery-gap] Recovery ≠ diagnosis — eval recovery as a separate, harder metric
**Rule:** Never declare a recovery loop "done" because attribution accuracy is high; correct root-cause identification does NOT imply the agent can act on it. Instrument and eval the recovery step independently.
**Evidence:** PROBE (arxiv 2605.08717, May 2026): three-layer telemetry→diagnosis→bounded-guidance framework hits 65.4% Top-1 diagnosis accuracy on 257 unresolved SWE cases but only 21.8% recovery success — the diagnosis–recovery gap.

### [KB:structured-output] Prefer constrained decoding over validation+retry
**Rule:** Use constrained decoding (translates schema to grammar, masks invalid tokens — invalid output literally cannot generate) as the default; treat validation+retry (Instructor/Guardrails AI) as a conscious tradeoff, not the path of least resistance. Measure output accuracy AND task accuracy. Treat schema-key wording as part of the instruction surface.
**Evidence:** Constrained-decoding benchmark (arxiv 2501.10868): constrained decoding (XGrammar, llguidance) achieves near-zero overhead while guaranteeing schema conformance across providers and complexity — the case is closed. DCCD (arxiv 2603.03305, Mar 2026): training-free two-stage decoder — unconstrained semantic draft then constrained decoding conditioned on it — removes the quality regression of naive constrained decoding, retiring the last argument for validation+retry. When Correct Isn't Usable (arxiv 2605.02363, May 2026): 7–9B models hit 85% task accuracy on GSM8K but 0% output accuracy; GPT-4o also collapses to 0% under reference prompting; AloLab meta-agent recovers SLMs to 84–87% without fine-tuning. Schema Key Wording (arxiv 2604.14862, Apr 2026): holding prompts/models/grammars constant and varying only schema-key wording moves accuracy measurably — don't autogenerate field names from DB columns.

---

## Safety & Guardrails

### [KB:guardrail-stack] Layer guardrails at input, flow, and output — outside the agent loop
**Rule:** Layer input (injection/jailbreak prevention) + flow control + output validation, positioned as an agent control plane *outside* execution loops; align to OWASP Agentic Top 10 (ASI01–ASI10) under a "least agency" principle.
**Evidence:** OWASP Top 10 for Agentic Applications (Dec 2025): industry-standard, peer-reviewed by 100+ experts; 10 Agentic Security Issues (Goal Hijack, Memory Poisoning, Tool Misuse, Inter-Agent Comms); "least agency" as governing principle. Microsoft Agent Governance Toolkit (Apr 2026): open-source 7-package toolkit (Python/TS/Rust/Go/.NET), zero-trust identity + sandboxing + policy + SRE-for-agents at sub-ms latency; first to cover all 10 OWASP Agentic risks; integrates LangChain/CrewAI/Google ADK/OpenAI Agents SDK. "Agent control plane" pattern: governance outside the loop for independent oversight; most teams layer NeMo (input/flow) + Guardrails AI (output).

### [KB:injection-defense] Use a provenance-aware injection defense — static filters are insufficient
**Rule:** For any agent receiving retrieved content (RAG, tool outputs, web), assume injection-by-default; deploy provenance-aware decision auditing and enforce request structure as priority-tiered segments, not concatenated text.
**Evidence:** ARGUS (arxiv 2605.03378, May 2026): provenance-aware decision auditing tracks untrusted-information flow into every decision — 3.8% ASR / 87.5% utility on AgentLure (4 domains, 8 vectors); current SOTA, auditability *is* the defense. PCFI — Prompt Control-Flow Integrity (arxiv 2603.18433, Mar 2026): models requests as system/dev/user/retrieved segments with hierarchical role-aware runtime policy — defense against goal hijack/tool-call abuse via priority enforcement.
**Trail:** superseded by ARGUS — ICON (arxiv 2602.20708): probing-to-mitigation indirect-injection defense, 0.4% ASR with >50% utility preserved.

### [KB:injection-impossibility] No filter is a complete answer — design for impact containment
**Rule:** Retire "we'll add an injection filter" as a complete defense; two independent impossibility results bound it. Architect for containment — least agency, action-boundary gating, provenance auditing — plus at least one of: training-time alignment, discontinuous filters at action boundaries, or architectural separation of deliberation from action.
**Evidence:** AI Agents May Always Fall for Prompt Injections (arxiv 2605.17634, May 2026): Contextual-Integrity impossibility — any norm-based filter tight enough to block an injection can be bypassed by a context where the malicious flow looks legitimate, while tightening over-blocks legitimate requests. Defense Trilemma (arxiv 2604.06436, Apr 2026): Lean-4 impossibility proof (360+ theorems) — no continuous, utility-preserving wrapper defense can make all outputs safe. The two converge from different formalisms.

### [KB:tool-exec-sandbox] Treat tool-execution surfaces as untrusted RPC — sandbox below the language layer
**Rule:** Prompt injection is now an RCE class. Sandbox any tool touching the filesystem; assume any retrieved/generated string can become a shell; layer process-level isolation (gVisor/Firecracker/microVMs) *beneath* any in-process interpreter sandbox — the language layer is not a trust boundary.
**Evidence:** Semantic Kernel CVEs (Microsoft Security, May 7 2026): CVE-2026-26030 + CVE-2026-25592 — unsafe string interpolation in filter functions + exposed file-write tools turn prompt injection into arbitrary code execution. vm2 Sandbox-Escape CVE Wave (Kodem Security, May 14 2026): 13 CVEs CVSS 9.0–10.0 chain prompt injection → JS-sandbox escape → host RCE; mitigation generalizes — process-level isolation beneath the language sandbox.

### [KB:agent-identity] Agent identity & MCP auth is the load-bearing security gap
**Rule:** For any MCP-wired or multi-agent system, verify per-agent identity, scoped least-privilege credentials, and delegation provenance; flag OAuth token pass-through and over-broad scopes as HIGH. Identity tracing, not content filtering, is the dominant MCP weakness.
**Evidence:** MCP Security at RSAC 2026 (Coalition for Secure AI, Apr 29 2026): ~38% of MCP servers ship with no auth; confused-deputy via OAuth token pass-through (vs RFC 8693 exchange) + over-broad scopes are the leading exploit patterns. AI Identity (arxiv 2604.23280, Apr 2026): five structural gaps blocking human→agent identity frameworks — semantic intent verification, recursive-delegation accountability, agent identity integrity, governance opacity, operational sustainability.

### [KB:abstention] Make abstention a first-class architectural primitive
**Rule:** Give every high-stakes decision a sanctioned non-decision path (escalate / typed insufficient-context result / safe deterministic fallback); silence-and-guess is never the default. Where the model can answer partially, hedge specificity rather than refuse outright.
**Evidence:** Calibrated Claim-Level Specificity (arxiv 2604.17487, Apr 2026): localized semantic backoff at claim granularity — emit *less specific* claims when confidence drops on sub-parts, instead of binary answer/refuse; preserves utility where global refusal tanks it. (Confidence gating: see [KB:hitl]. Guaranteed recovery path: see [KB:diagnosis-recovery-gap].)

### [KB:gap-signals] Route every abstention and caught hallucination to a queryable sink
**Rule:** Each escape-hatch trip and caught hallucination is a labeled gap signal — emit a structured event `{decision_point, missing_resource, confidence, inputs_hash, timestamp}` to a queryable store, aggregate by decision point, rank by frequency × cost, feed top gaps into the build backlog. A hatch with no durable sink is theater.
**Evidence:** Synthesized from the Cross-Cutting Principle (Anthropic progressive-disclosure guidance + the abstention/selective-prediction literature). Hallucination is often a resourcing failure, not a model defect: an agent forced to act without needed context and with no sanctioned way to decline. Complements [KB:failure-attribution] (why a run failed) — gap signals say what's structurally missing. Abstentions are the highest-information points in traffic; they mark the competence boundary (active learning for the product surface).

### [KB:hitl] Gate HITL on calibrated trajectory-level confidence, automate selectively
**Rule:** Choose an oversight pattern by risk (multi-tier / synchronous approval / async audit); set confidence thresholds by domain (financial 90–95%, routine CX 80–85%; target escalation 10–15%, 60%+ signals miscalibration); drive the threshold from trajectory-level confidence, not uncalibrated self-report; automate selectively, not comprehensively.
**Evidence:** Holistic Trajectory Calibration / HTC (arxiv 2601.15778): estimates success likelihood from the entire execution trajectory, not just final output — principled uncertainty thresholds for HITL, replacing hand-tuned heuristics. Klarna cautionary tale: 2.3M conversations/month, 80% faster resolution, ~$40M projected — then rehired humans when complex cases hit dead-end conversations → automate selectively. (Claim-level hedging complement: see [KB:abstention].)

---

## Compliance

### [KB:eu-ai-act] EU AI Act — high-risk delayed to Dec 2 2027, but transparency still binds Aug 2 2026
**Rule:** For any EU-deployed or EU-user-touching agent, build ≥6-month log retention + override mechanisms + external-monitoring data flows (Articles 19/26); flag missing infra as HIGH. The high-risk delay does NOT cover transparency — Article 50(1) interaction-disclosure still binds Aug 2 2026; flag missing disclosure as HIGH on the unchanged clock. Don't dismantle infra already built for the original deadline.
**Evidence:** EU AI Act Council–Parliament Provisional Agreement (consilium.europa.eu, May 7 2026): high-risk applicability for stand-alone systems shifted Aug 2 2026 → Dec 2 2027; Articles 19/26 unchanged; penalties unchanged up to €15M or 3% global turnover; final adoption pending. EC Draft Guidelines on AI Transparency (May 2026): Article 50(1) disclosure (a deployer must disclose when a human is *likely* interacting with an AI agent) unchanged at Aug 2 2026, plus multi-layered synthetic-content marking (no single watermark sufficient); providers handle upstream marking, deployers bear downstream disclosure.

### [KB:nist] Pair EU/OWASP with NIST as the emerging compliance triangle
**Rule:** Track the NIST voluntary US-side governance track (agent identity/auth, JIT access, action-level approvals) alongside OWASP/MS Toolkit (technical) and EU AI Act (regulatory).
**Evidence:** NIST AI Agent Standards Initiative (nist.gov/caisi, active Q2 2026): voluntary track covering agent identity/auth, least-privilege & JIT access, action-level approvals for high-impact decisions; AI Agent Interoperability Profile due Q4 2026.

### [KB:compliance-properties] Build the five compliance properties for regulated deployments
**Rule:** For regulated deployments, implement traceability, explainability, authorization, immutability, reproducibility — plus kill switches tied to error-rate thresholds and incident-freeze protocols. These map directly to AI Act requirements.
**Evidence:** KPMG (75% of leaders rank these most crucial): traceability (OTel event emission + JSON structured logging), explainability (MCP as flight recorder for prompts/tool calls/reasoning), authorization (action-level permission gates), immutability (write-once S3 tiering + cryptographic signatures), reproducibility (deterministic fallback paths). Sector overlays: financial services — missing agent traces = books-and-records violations; HIPAA — 6-year retention; FDA — technical documentation for clinical products. Kill switches with 2-hour review windows are non-negotiable.

---

## Cost

### [KB:cost-optimization] Tier models, cache the right layers, batch, minimize output tokens
**Rule:** Apply the cost-strategies stack (model routing, prompt caching, semantic caching, agentic plan caching, batching, output-token minimization) — see the table under Reference Tables. Output tokens dominate agent spend; optimize for fewer, more effective tool calls.
**Evidence:** Model routing going mainstream (IDC): 70% of top AI-driven enterprises projected to use dynamic multi-model routing by 2028 — optimization tip → foundational pattern. Token-economics grounding (arxiv 2605.09104, May 2026): output-token spend multiplies across later turns. (Strategy detail + reduction figures: see Reference Tables → cost-strategies.)

### [KB:cost-accuracy] Optimizing for accuracy alone is an order-of-magnitude cost tax
**Rule:** Never tune for quality alone — measure the multi-dimensional tradeoff (cost, latency, efficacy, assurance, reliability) explicitly.
**Evidence:** CLEAR (arxiv 2511.14136): agents tuned for accuracy alone end up 4.4–10.8× more expensive than cost-aware alternatives at comparable performance.

### [KB:cache-pitfall] Don't cache full context — cache stable layers only
**Rule:** Cache the system prompt and stable tool specs; exclude dynamic tool results and per-step context. The default "cache everything you can" harness pattern is wrong for long-horizon agents.
**Evidence:** Don't Break the Cache (arxiv 2601.06007): first cross-provider eval of prompt caching for long-horizon agents — strategic caching cuts API cost 41–80% and TTFT 13–31%, but naive full-context caching can paradoxically *increase* latency.

### [KB:semantic-cache] Use error-guaranteed semantic + plan caching
**Rule:** Use a semantic cache with a user-defined error rate (online-learned per-prompt thresholds) instead of "pick a threshold and pray"; reuse structured plan templates for recurring plans.
**Evidence:** vCache (arxiv 2502.03771): first semantic cache with user-defined error-rate guarantees via online learning of per-prompt similarity thresholds. Agentic Plan Caching (arxiv 2506.14852): store/reuse structured plan templates — 50% cost, 27% latency reduction.

### [KB:routing-cascades] Validate that cascading actually beats a tuned single-tier threshold
**Rule:** Don't reflexively cascade — model routing as a provider/user game and confirm escalation beats a tuned static threshold for your traffic.
**Evidence:** Routing/Cascades game theory (arxiv 2602.09902, Feb 2026): Stackelberg game between cost-minimizing providers and utility-maximizing users (who re-prompt or abandon) — optimal policy is often a static threshold with no cascading; cascading can degrade outcomes under incentive misalignment.

### [KB:planning-efficiency] Plan once, replan on deviation; compile recurring loops; skip unnecessary tool calls
**Rule:** Don't assume eager step-by-step reasoning is required — use full-horizon planning + lazy replanning when task structure is knowable up front; compile recurring tool-call patterns into deterministic meta-tools; read the latent tool-necessity signal to cut redundant calls.
**Evidence:** Do Agents Need to Plan Step-by-Step? (arxiv 2605.08477, May 2026): full-horizon planning + lazy replanning matches eager step-by-step accuracy at 2–3× fewer tokens on data-centric tool-calling. Probe&Prefill (arxiv 2605.09252, May 2026): tool-necessity is linearly decodable from pre-generation hidden states (AUROC 0.89–0.96); reading the latent signal cuts unnecessary tool calls ~48% with minimal accuracy loss — over-calling is a decoding-behavior problem, not a knowledge gap. AWO (arxiv 2601.22037): compile recurring tool-call patterns into deterministic meta-tools — −11.9% LLM calls, +4.2pp success.

---

## Continuous Improvement

### [KB:trace-loop] Run the trace-driven improvement loop; encode every failure as a permanent eval
**Rule:** Collect production traces → enrich with evaluator scores + human annotation → identify recurring failure patterns → make targeted prompt/tool/orchestration changes → validate offline against curated datasets → deploy via canary/feature flags → repeat. Every failure mode encoded as an eval stays in the suite permanently to prevent regression.
**Evidence:** Industry-converged cycle (synthesized from Anthropic eval methodology + LangChain/Databricks production data). Rollout: rainbow deployments shift traffic between agent versions without disrupting running agents.

### [KB:prompt-optimization] Programmatic prompt optimization first; capability-targeted training when it plateaus
**Rule:** Use programmatic prompt optimization (typed signatures, compiled, transfers across models) as the cheap first move; when prompting plateaus on a capability gap, do capability-targeted lightweight training reusing the same trajectory-contrast data.
**Evidence:** TRACE (arxiv 2604.05336, Apr 2026): contrasts successful vs failed trajectories to diagnose missing capabilities, synthesizes targeted RL environments per gap, trains LoRA adapters, routes at inference — +14.1 pts τ²-bench, beats GRPO and GEPA on scaling efficiency. ACE evolving playbooks (arxiv 2510.04618, ICLR 2026): see [KB:context-eng]. DSPy / GEPA (Stanford NLP): typed signatures + optimizer auto-find prompts (ReAct 24%→51% HotPotQA, transfers across models); GEPA (Genetic-Pareto) supersedes MIPROv2 — trajectory sampling + NL reflection + Pareto frontier, in OpenAI's self-evolving agent cookbook.

### [KB:self-improvement] Continuous improvement doesn't require fine-tuning — invest in episodic memory
**Rule:** For most production agents, invest self-improvement budget in episodic-memory infrastructure (with a security-grade channel), not training pipelines; invoke stored experience selectively at high-uncertainty points, not always.
**Evidence:** ShinkaEvolve (Sakana AI, ICLR 2026 RSI workshop): self-improving evolutionary search discovered a novel MoE load-balancing loss surpassing DeepSeek SOTA in 30 generations — real transferable artifacts, not leaderboard gaming. Memento (arxiv 2508.16153): memory-augmented online RL (M-MDP) adapts via episodic case memory without touching base weights — top-1 GAIA validation (87.88% Pass@3), +4.7–9.6% on OOD vs training-heavy baselines. Continual Learning Moves to Memory (arxiv 2604.27003, Apr 2026): experience-reuse via external memory often outperforms gradient-based continual learning. ExpWeaver (arxiv 2605.07164, May 2026): treat stored experience as an optional resource invoked only at high-uncertainty decision points — beats rigid always-inject. MAGE Shadow Memory (arxiv 2605.03228, May 2026): security-grade memory channel — see [KB:memory-security]. Continual Harness (arxiv 2605.09998, May 2026): agents refine own prompts/sub-agents/skills/memory without env resets; co-learning where open-source agents improve via frontier-teacher feedback during execution.

---

## Observability

### [KB:otel] Use OTel GenAI semantic conventions as the agent-tracing standard
**Rule:** Instrument distributed tracing with OpenTelemetry GenAI semantic conventions — `invoke_agent` spans, W3C trace-context propagation through MCP — as the interoperability layer, not a nice-to-have; add semantic drift detection and circuit breakers for long-running ops.
**Evidence:** OTel GenAI semantic conventions v1.37–v1.41 (mid-2026): dedicated `invoke_agent` spans break agent reasoning out of the opaque single-LLM-call black box; v1.39 MCP conventions wire W3C trace-context propagation through MCP servers (tool-server traces no longer disconnected islands); three content-capture modes for privacy-vs-debuggability. Red Hat OTel Agent Observability Guide (Apr 2026): end-to-end OTel instrumentation for multi-hop agentic workflows with concrete span/trace patterns. Semantic drift detection: Arize Phoenix compares outputs against baseline via embedding similarity, statistical anomaly detection (not static thresholds).

---

## Industry & Eval Integrity

### [KB:industry-data] The deploy-vs-succeed gap is real, governance/evals are the causal levers
**Rule:** Anchor production-readiness conversations in primary-source data: most projects don't reach scale, deployment ≠ success, and governance + evals are what actually graduate agents to production.
**Evidence:** Databricks 2026 State of AI Agents (20,000+ orgs, 60%+ of F500): governance → 12× more projects shipped to production, eval tooling → 6× production graduation; multi-agent workflows grew 327% in <4 months — strongest pilot-to-production causal data. Gartner (May 26 2026): 40% of enterprises will demote/decommission agents by 2027, root cause is binary governance — scale proportional controls across four autonomy levels (Observe/Advise/Act-with-Approval/Act-Autonomously). Gartner (Apr 28 2026): only 18% maintain a complete current agent inventory, 50% of agents in isolated silos, 27% of inter-agent API connections fully ungoverned, 1,600+ agents/enterprise projected by end-2026. Supporting stats: 5% of GenAI projects reach scale (MIT); 40% of agentic projects predicted canceled by end-2027 on cost/value (Gartner); 57% have agents in production but only 14% truly production-ready (G2, Aug 2025); 97% deployed but only 34% report success, KPMG Q1 2026; pilot-to-production ROI only 1.7×, only 6% high performers (McKinsey 2025); orchestration layer is the durable advantage, model interchangeable in 42% of cases (Stanford Enterprise AI Playbook); eval adoption gap 52% offline / 37% online (LangChain); supervision gap — 36% no supervision plan, 35% can't pull the plug, 67% suspect a shadow-AI leak (Writer 2026); sprawl 94% concerned / 12% with a platform (OutSystems 2026); 50% of orgs WITH AI controls still hit by incidents, 52% lack detection confidence (Proofpoint 2026); success metrics migrating productivity → P&L, financial impact ~21.7% of primary metrics (Futurum, Apr 2026); State of FinOps 2026 (1,192 respondents, $83B+ tracked) — AI spend 31%→98% of FinOps scope in two years, agents run a triple cost meter (tokens-per-model + runtime-per-hour + per-call tool charges) traditional tooling can't attribute. Org-friction frames: HBR (Mar 2026) seven structural frictions; Berkeley CMR "Governing the Agentic Enterprise" (Mar 2026) four-layer Agentic Operating Model (Cognitive/Coordination/Control/Governance); Forrester Predictions 2026 — only 15% reported EBITDA lift, <1/3 tie AI to P&L, ~25% of spend deferred to 2027; AI intensifies work rather than reducing it — employees work faster and absorb broader responsibilities (University of Michigan).

### [KB:benchmark-contamination] Trust adversarial held-out evals you build over public leaderboards
**Rule:** Don't trust public leaderboard numbers — leading benchmarks are contaminated/exploitable; build held-out adversarial evals, and for long-horizon work use a synthetic sim you control. Watch scratchpad persistence as the strongest long-horizon predictor.
**Evidence:** Berkeley RDI — How We Broke Top AI Agent Benchmarks (Apr 2026): all 8 leading agent benchmarks (SWE-bench, WebArena, OSWorld, GAIA, Terminal-Bench, FieldWorkArena, CAR-bench, et al.) exploitable to near-perfect scores. SWE-bench Pro (1,865 multi-language tasks): replaces contaminated SWE-bench Verified, real ceiling ~46% (not 81%); same model varies 50–55% on scaffolding — context engineering > model choice; distilled small models can beat their teachers (Magnet-14B > Gemini-1.5-pro on function calling), so model size is not destiny. YC-Bench (arxiv 2604.01212, Apr 2026): contamination-immune 52-week startup sim — scratchpad persistence is the single strongest predictor of long-horizon success; failure to detect adversarial clients drives ~50% of simulated bankruptcies across 12 models. Compendium: Phil Schmid's AI Agent Benchmark Compendium (50+ benchmarks).

---

## Reference Tables

### [KB:frameworks] Orchestration framework selection
**Rule:** Match the framework to the job; default to the lightest that fits.

| Framework | Sweet Spot |
|-----------|-----------|
| LangGraph | Stateful, mission-critical, maximum control |
| CrewAI | Rapid prototyping, role-based crews |
| AutoGen / MS Agent Framework | Conversational multi-agent (higher cost) |
| OpenAI Agents SDK | Lightweight, handoff-based |
| Claude Agent SDK | Lifecycle hooks, filesystem-heavy tasks |
| DSPy / GEPA optimizer | Programmatic prompt optimization, compiled reliability (GEPA succeeds MIPROv2) |

### [KB:eval-tools] Evaluation tooling selection
**Rule:** Pick eval tooling by deployment surface and openness; CI-gate the automated layer.

| Tool | Type | Strength |
|------|------|----------|
| Braintrust | Commercial | Trajectory scoring, prompt playground |
| LangSmith | Commercial | LangChain-native, annotation queues |
| DeepEval | Open-source | 30+ metrics, pytest CI/CD integration |
| Langfuse | Open-source | Self-hostable, tracing + prompt management |
| Arize Phoenix | Open-source | Embedding drift detection, deep tracing |
| RAGAS | Open-source | RAG pipeline evaluation standard |

### [KB:guardrail-tools] Guardrail tooling selection
**Rule:** Layer input/flow + output + security guardrails; map to OWASP Agentic Top 10.

| Tool | Role | Strength |
|------|------|----------|
| NVIDIA NeMo Guardrails | Input/flow control | Colang DSL, sub-100ms, open-source |
| Guardrails AI | Output validation | 50+ composable Pydantic validators |
| Galileo (Luna-2 SLMs) | Evaluation | 0.95 F1 at 98% lower cost than LLM judges |
| Lakera | Security firewall | Single API for prompt injection/jailbreak prevention |
| Azure AI Content Safety | Content moderation | 0–6 severity scoring, Prompt Shields |
| OWASP Agentic Top 10 | Compliance framework | ASI01–ASI10 risk taxonomy for agentic systems |
| MS Agent Governance Toolkit | Open-source governance | Covers all OWASP Agentic Top 10 risks, framework-agnostic |

### [KB:cost-strategies] Cost optimization strategies (47–80% reduction achievable)
**Rule:** Apply in ROI order; output tokens dominate agent spend.

- **Model routing (tiered)** — Tier 1 (Haiku/GPT-4o-mini) classification, Tier 2 (Sonnet/GPT-4o) moderate, Tier 3 (Opus) complex; cheap-model failures escalate upward. (Validate cascading vs static threshold: see [KB:routing-cascades].)
- **Prompt caching** — highest-ROI single optimization. (Cache stable layers only: see [KB:cache-pitfall].)
- **Semantic caching** — embedding similarity cuts inference cost up to 73%. (Error-guaranteed: see [KB:semantic-cache].)
- **Agentic plan caching** — reuse structured plan templates: 50% cost, 27% latency reduction.
- **Batching** — 50% token discount for batch workloads (OpenAI + Anthropic, as of Apr 2026).
- **Key insight** — output tokens dominate agent spend; optimize for fewer, more effective tool calls. (Cut redundant calls: see [KB:planning-efficiency].)
