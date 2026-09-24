# Research handoff (T012 local contract)

DSCC can record a research project's questions, evidence, plans, observations, failures and current state, then return an explicit state with its original ancestor artifacts. This works through the existing node store, CLI and MCP. It does not invoke models, run experiments or publish records.

## Start and resume

```sh
python -m dscc --home ~/.dscc init
python -m dscc --home ~/.dscc research-record --file examples/research_state.json
# Use the CID returned above:
python -m dscc --home ~/.dscc research-handoff STATE_CID
```

The example is an initial state with no claimed findings. Replace its content with the actual project and contributor context. Record original source artifacts first with the existing `record`/`record_artifact` interfaces; then reference them from research profiles. Keep source URLs, bibliographic identifiers, relevant excerpts/locations and licensing in those original artifacts. The service resolves local source references and never downloads URLs.

MCP adds `record_research({payload, license?})` and `get_research_handoff({state_cid})`. Python applications use `ResearchService(node).record(payload, license=...)` and `.handoff(state_cid)` from `dscc.research`. All three adapters use the same validator/service.

For another node, the owner explicitly exports `STATE_CID` with the existing `export` command and imports it using the existing `import --trust-key` command. Inspect the whole ancestor closure before sharing: it includes source content, not only the latest summary. The handoff response is a local read, not a file export or publication action. Separate node homes remain the confidentiality boundary; `project` is a label, not an ACL.

## Versioned profile

Top-level fields are exactly `schema`, `type`, `project`, `title`, `summary`, `contributor`, `input_cids`, `sources`, `relations`, `content`. Schema is `dscc.research/0.1`. Contributor fields are `kind` (human/agent/unknown), `name`, `provider`, `model`, `snapshot`; unavailable provider/model/snapshot identifiers must be null. These are declared metadata, not authenticated model identity. A node signature authenticates the signing key only.

| Research type | Existing seed kind | Required content fields |
|---|---|---|
| ResearchQuestion | Task | question (text), evaluation_criteria (nonempty text list) |
| LiteratureReview | MemoryCapsule | known_results, open_questions (text lists) |
| Hypothesis | Claim | statement, rationale (text) |
| ExperimentPlan | Workflow | question_cid, procedure (text), evaluation_criteria (nonempty text list) |
| EvaluationRun | ExperimentRun | plan_cid, observations (object), interpretation (text) |
| FailureReport | MemoryCapsule | attempted, observed (text), remaining_questions (text list) |
| OpenQuestion | Task | question (text) |
| ResearchState | MemoryCapsule | objective (text), finding_cids, open_question_cids, resume_cids (CID lists), next_actions (text list) |
| AgentContribution | DecisionRecord | description (text) |

`input_cids` identifies the artifacts used to produce the contribution. A `source` has exactly `cid`, `pointer`, `role`. Roles are primary_literature, observation, code, configuration, data, context. Pointers use RFC 6901 string syntax, rooted at the signed envelope, e.g. `/body/data/measurements/0`. The empty pointer selects that envelope. `/cid` and `/content_trust` are fetch-only metadata and cannot be source locations. Arrays use canonical nonnegative indices; `-`, leading-zero indices and invalid escapes are rejected.

A literature review with known results requires a primary_literature source. Evaluation and failure reports require an observation source. These checks establish recoverable declared evidence, not whether the cited material really proves the statements. Keep interpretation separate from observations and create separate profiles when finer statement-to-source attribution is needed. A finding reference may point to a hypothesis; its original type is retained rather than promoted to a measured fact.

A relation has exactly `type`, `target_cid`, `rationale`. Types are supports, contradicts, supersedes, replicates. The relation remains an assertion by the contributing artifact. A supersession must target the same research type and project; previous states remain accessible. Cross-project inputs/evidence are allowed. Experiment plans reference ResearchQuestion/OpenQuestion; evaluations reference ExperimentPlan; state open-question references point to question profiles.

All recognized CID fields, sources and relation targets become parents automatically. Unknown top-level or content fields are rejected; optional `content.extensions` is an object for namespaced domain-specific data. Extensions are preserved but not interpreted as execution instructions or undeclared dependencies. Use explicit inputs/sources for extension dependencies. Text/list/record bounds follow `research.py` and the existing seed. Metadata decimal values remain strings, with units where appropriate.

## Handoff semantics

`dscc.research.handoff/0.1` contains the selected state, a typed record inventory, original signed artifacts, declared relations, contradiction/supersession assertions and repeated-work candidates. The complete ancestor closure is validated before returning. Missing, tampered or malformed referenced research records cause an error; no partial handoff is returned as complete. Generic-record imports cannot bypass this validation.

Repeated-work fingerprints cover exactly the canonical schema/type/project/input_cids/sources/content fields. They exclude contributor, title, summary and relations; arrays retain their order. Matching fingerprints identify exact declared-work candidates, not semantic duplicates or independent replications. Contradictions are explicitly recorded relations; the service does not infer contradictory prose. No graph or record is deleted to deduplicate it.

`complete_ancestor_closure` refers to signed small-record ancestors only. Model weights and other large binary blocks are not included (`large_blocks_included: false`). The selected state is explicit: callers can examine several branches rather than trusting a wall-clock winner. The response retains `content_trust: untrusted_research_data`, `scientific_correctness: not_assessed`, `execution_authorized: false`, and `published: false`.

## Reproduce the contract tests

```sh
python -m pytest -q tests/test_research.py tests/test_research_stdio.py
python -m pytest -q
python -m dscc demo
python scripts/check_repository.py
```

The tests use synthetic research and contributor labels, three local node directories, real CLI/MCP subprocesses, and explicit owner-controlled bundle exchange. No real provider/model is invoked. T012 stays open for actual cross-model research-quality experiments and later orchestration. See ADR-0005, T012 and the PR's observed CI evidence.
