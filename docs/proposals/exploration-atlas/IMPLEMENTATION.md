# Exploration Atlas: algorithms, interfaces and implementation plan

Status: implementation proposal, not a shipped feature. Main explanation: [日本語構想案](../EXPLORATION_ATLAS.ja.md). All numeric settings below are configurable starting points, not measured optima or restrictions on the final design.

## 1. Package boundaries

Proposed new modules:

```text
src/dscc/atlas/
  contracts.py      # payload + referential validation, no execution
  adapters.py       # native run events / annotated notes / optional LLM extraction
  index.py          # separate derived SQLite catalog + vector-store adapters
  features.py       # versioned multi-view and directed structural features
  retrieval.py      # independent candidate streams and rank fusion
  alignment.py      # explicit partial relation-preserving correspondence
  transfer.py       # proposed bridges, reported trials, source lineage
  service.py        # permission-scoped public interfaces
```

No application module in the proposed tree above is introduced by this commit. The accompanying helpers implement offline example validation and a small structural-feature reference only. Do not treat them as a network-facing validator or sandbox. T007 owns the source/catalog boundary; T001 owns service authority; T002 owns MCP registration; T004 owns desktop rendering; T005 owns peer transport. Coordinate changes rather than expanding those tasks silently.

## 2. IDs, envelopes and sources

Wrap each payload with the existing signed seed envelope: `MemoryCapsule.data.atlas` for Episode/Motif, `EvidenceLink.data.atlas` for Bridge/TransferAssessment. The existing `parents` contain every distinct external CID used by the payload, including source locators. Enforce the current parent and byte limits; return `needs_segmentation` rather than truncating. Segmentation must preserve continuation and branch links. Large closed ancestry bundles require the separately planned chunked storage transport.

Schema URI: `urn:dscc:atlas:0.1-draft`. `node.id` and `link.id` are local to their containing episode. External node references are `(episode_cid, node_id)`. IDs never depend on text embeddings or UI coordinates.

`SourceRef = {cid, pointer}` addresses the canonical signed source envelope, with RFC 6901 JSON Pointer syntax. Follow `~1` and `~0` escaping, support the empty pointer, reject noncanonical array indexes and out-of-range pointers. A locator is evidence of provenance, not an assertion that the source is true. Fetch through the existing integrity-checked store.

The reference schema validates shape only. Runtime validation must additionally check unique IDs, endpoint existence, all source locators, acyclic `precedes`, one-to-one bridge bindings, matched edge endpoints and types, bridge/trial object types, and source ancestry. Source access or validation failure cannot silently become an observed result.

## 3. Native events versus interpretation

For a machine run, import input/tool/output CIDs and events directly. Store exact metrics and units in the source; copy summaries only with references. For prose, keep the prose and add extracted nodes. Tag origin as logged, self_report, model_extracted, synthetic or unknown. A model-extracted relation is not upgraded to logged merely because its source has a signature.

Record extractor model digest/revision, input locators, prompt/profile digest and configuration in a separate provenance object when needed. An alternate extraction creates an alternate episode. Do not collapse competing interpretations by writer-model size. Extraction is incremental and cached; generative calls are optional for retrieval but not magically unnecessary for interpreting arbitrary prose.

Keep observations, expectations and interpretations as different roles. For example, a participant's expectation about a relationship is not an observation of another person's motives. Do not infer a complete state from a missing log. Proposed and stopped branches remain distinguishable from performed actions.

## 4. Derived storage and transactions

Use a separate SQLite database for derived metadata, with a generation ID and foreign keys inside that database. The authoritative source store is read-only to indexing. Suggested tables:

```text
episodes(cid PK, source_set_digest, extractor_profile, state, generation)
nodes(episode_cid, node_id, role, stage, origin, source_refs, PRIMARY KEY(...))
links(episode_cid, link_id, src, dst, relation, origin, source_refs, PRIMARY KEY(...))
features(episode_cid, profile_id, view, vector_ref, generation, PRIMARY KEY(...))
bridges(cid PK, source_episode, target_episode, generator_profile)
assessments(cid PK, bridge_cid, trial_episode, verdict, evaluator_ref)
motif_members(motif_cid, member_episode, alignment_ref, PRIMARY KEY(...))
index_jobs(source_cid, profile_id, state, last_error, generation, PRIMARY KEY(...))
```

Maintain a rebuildable FTS index and a separate compatible vector index. Pin snapshots of source IDs while rebuilding. Build the next generation completely, validate counts/dependencies, then atomically update the active generation pointer. A crash retains the old generation. Parent/descendant invalidation follows source references, not wall-clock timestamps.

A practical local adapter may use SQLite FTS5, NumPy/SciPy sparse matrices and an optional HNSW implementation. Pin dependencies when actually selected; these are library choices, not a requirement to reimplement databases. Ship an exact-search fallback for small permitted collections and compare ANN recall against it. Do not mix ACL domains in an index then hope a final result filter prevents leakage.

## 5. Profiles and views

Maintain separate views for topic, goal, intervention and structure. The profile ID is the digest of a canonical profile describing encoder weights/revision, tokenizer, extraction/chunking, query/document templates, pooling, dimension, normalization, number representation and adapter version. Structural profiles additionally identify node/edge label vocabularies, directedness, feature algorithm, iteration depth and hash encoding.

Zero/nonfinite vectors are marked unavailable, not normalized. New encoders run side-by-side with old ones before switch-over. Do not compare incompatible vectors directly. A changed feature profile creates a new index without changing the episode CID.

### Directed structural reference

For episode graph G=(V,E), use initial labels `(role, stage, origin)`. Including origin prevents performed source logs and hypothetical stories from becoming indistinguishable in the default profile. Alternative views may mask origin deliberately, but must declare this and must never transfer that masking to evidence classification.

For rounds t=0..h (initial h=2):

```text
l_0(v) = SHA256(canonical_json([role(v), stage(v), origin(v)]))
l_(t+1)(v) = SHA256(canonical_json([
    l_t(v),
    sorted([relation(e), l_t(src(e))] for incoming e),
    sorted([relation(e), l_t(dst(e))] for outgoing e)
]))
phi(G) = histogram((t, l_t(v)) for each round and node)
K(G,H) = dot(phi(G),phi(H)) / (norm(phi(G))*norm(phi(H)))
```

Incoming/outgoing multisets preserve direction, type and multiplicity; IDs and array order do not enter the labels. Sort encoded tuples deterministically; do not use Python's randomized `hash()`. This is a directed, typed adaptation inspired by WL, not an exact copy of the original undirected kernel or a complete isomorphism test. Cost is bounded by h passes over adjacency plus sorting, roughly O(h(|V|+|E|) log d_max), not an all-corpus graph comparison.

Sparse feature indexes or sketches can retrieve candidates. If sketches introduce collisions, rerank against full features. Do not put object names into the only structural view: it defeats cross-domain retrieval. Conversely, role topology alone is too coarse; candidate matches still need semantic/relational checks.

## 6. Retrieval and alignment

1. Resolve the caller's permitted collection and requested mode before generating candidates. In the current seed use separate node homes for different confidentiality domains.
2. Build topic/goal/intervention embeddings and structural query features. A user-supplied episode works without generative query parsing; a natural-language query may optionally use a cached parser. Report missing query structure.
3. Independently retrieve lexical, semantic and structural candidates. Start with 50 per stream, configurable. A structural candidate must be able to enter even when outside the semantic top-k.
4. Fuse ranks, e.g. `RRF(x)=sum_j w_j/(60+rank_j(x))`, with documented weights. Missing candidates contribute nothing. This is an initial heuristic, not a calibrated probability. Deduplicate identical CIDs and group copied source lineages for presentation while retaining originals.
5. Align small relevant subgraphs of leading candidates. Return several alternatives when ambiguous. Use role-compatible candidate bindings, then check edge direction, relation and local predecessor consistency. A maximum-weight bipartite assignment with dummy unmatched nodes can initialize a mapping; follow with beam/local search over edge consistency. Node assignment alone does not solve graph matching. Permit partial mappings and expose gaps.
6. Retrieve original conditions, observations, later corrections and proposed branches around the match. PageRank may expand context on the permitted evidence graph; its rank is not the alignment score or truth score.
7. Produce a Bridge proposal with concrete bindings, matched edges, mismatches and a next question. Never issue an action merely because a bridge scores highly.

Suggested alignment objective for a partial injective map M:

```text
score(M) = sum matched_node_scores
         + lambda * sum preserved_typed_directed_relations
         - mu * unmatched_relevant_structure
         - nu * contradicted_explicit_constraints
```

All terms and masks belong to a versioned profile. Compare only commensurate metrics with declared units. In `analogy` mode a domain difference is not a hard rejection: it is an explicit gap. In `transfer` mode preconditions for executable tool reuse must pass separately. Do not require a GPU optimization and a personal experience to share units or objectives.

Use configurable CPU/time/visited-pair budgets (e.g. an initial 20 candidates, 64 active nodes per candidate window, beam width 16). These are execution budgets, not storage or conceptual limits. Large episodes remain intact; return a continuation cursor and `truncated=true` plus inspected coverage. Start with lossless variable-size windows and let evaluation determine batching/caching. Do not reshape the stored design to make benchmarks easy.

PPR context expansion uses `p_next=(1-alpha)q+alpha*P.T*p`, with nonnegative row-normalized P, alpha initially 0.85, dangling mass returned to q, L1 residual threshold and iteration budget. Mark a budget-limited run as unconverged. Use observed provenance edges preferentially and keep hypothetical analogy edges distinguishable; a hub or copied text never creates additional independent evidence.

## 7. Proposed service contracts

These are future interfaces, not tools currently exposed by MCP. Keep existing `search_assets` unchanged and coordinate additions with T001/T002.

```text
record_exploration(payload, source_cids) -> {cid, local_only, indexing_state}
index_exploration(cid, profile_ids, budget) -> {generation, state, missing, costs}
search_exploration(query_text?, episode_cid?, mode, scope, profiles, budget)
  -> {candidates, searched_snapshot, incomplete, costs, next_cursor?}
get_exploration(cid, radius, budget)
  -> {nodes, links, sources, missing_sources, truncated, next_cursor?}
propose_bridge(source_episode, target_episode, profile, budget)
  -> {candidate_payload, mappings, gaps, evidence_refs, costs}
record_transfer(assessment_payload) -> {cid, local_only}
```

A search candidate contains episode CID, source locators, per-stream ranks, profile IDs, concrete mapped nodes/edges, known condition differences, available transfer-assessment CIDs and missing sources. Do not return a naked synthetic confidence number. Empty results mean no match in the permitted searched snapshot, not no match anywhere.

Use error codes `unsupported_profile`, `invalid_locator`, `missing_source`, `incompatible_profile`, `needs_segmentation`, `permission_denied`, `budget_exhausted`, `index_unavailable`. Permission failures must not disclose the hidden title or existence count. Idempotent index jobs use `(source_set_digest, profile_id)`; record writes produce new immutable objects. Nothing here adds job execution or public publication authority.

## 8. Motif induction and updates

Mine recurring typed substructures or compare aligned subgraphs, then retain explicit member mappings. Nameable high-level motifs may use an optional interpretation agent. Keep member sources, negative cases, scope, method and unresolved differences. Require held-out retrieval benefit or description-length improvement before preferring a new compressed representation; do not claim it is a scientific law.

Motifs overlap. New interpretations create new immutable motifs with `derived_from` provenance. If provenance would exceed a record, store member batches as ordinary artifacts and use paged traversal. Summaries or embeddings are replaceable views; source evidence is not disposable. Rebuilding the motif index must not reinterpret a proposed bridge as a tested transfer.

## 9. Evaluation without narrowing the design

### Contract tests provided now

Synthetic GPU, model-design and personal-learning paths exercise shape, IDs, pointers, branch states, edge direction and bridge/trial references. They are deliberately labeled synthetic. Passing them says nothing about useful analogies or real model performance. No API key, downloaded model, personal conversation or remote execution is required.

### Integration and quality work for the implementing agent

Use consented, license-compatible traces from independent projects, including at least performance engineering, model development and a nontechnical domain. Preserve sparse, noisy, contradictory and unfinished records. Keep project lineage and author-derived duplicates on one side of any train/test split; split by source group and time. When evaluating prefix queries, exclude the target episode's future observations from the index and query construction.

Label correspondence validity, useful next question and actual transfer outcomes separately, preferably with multiple reviewers and recorded disagreement. Include same-topic/different-structure decoys, different-topic/similar-structure cases, generic-chain false positives, role reversals, unsupported extracted causes and incompatible conditions. Evaluate extraction precision/recall against source spans as well as retrieval; a perfect hand-built graph is not evidence that the ingestion system works.

Report Recall@k and nDCG for independently labeled structural analogies, relation-mapping precision, exact source recovery, false analogy rate, negative-transfer rate, abstention, unknown/missing-source behavior, and downstream completion judged from external results. Record raw task metrics separately rather than averaging romance outcomes with engineering speedups.

Measure extraction/embedding/index build CPU/GPU seconds, bytes, peak RAM, per-query p50/p95 latency, visited nodes/edges, cost per verified useful retrieval and generation calls. Compare exact keyword, semantic, structural and combined designs on their quality–cost frontiers with settings suited to each. Ablations are derived from the full design, not constraints imposed to cripple it. Do not adopt permanent latency or quality claims from tiny synthetic examples.

### Release gates

No source loss on rebuild; unchanged legacy CID/signatures; no public/private cross-index leak; no incompatible-profile comparison; valid observed/proposed distinction; no unsupported promotion of bridges; deterministic feature tests; all existing regression tests; actual multi-model/client integration logged separately. Publish remaining gaps explicitly.
