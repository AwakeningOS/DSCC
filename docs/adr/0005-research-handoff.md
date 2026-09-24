# ADR-0005: Source-linked research profiles and explicit-state handoff

Status: proposed with T012's first implementation; effective on merge.

## Context and prior work

DSCC needs reusable research state across human/agent changes. W3C PROV-O already supplies Entity/Activity/Agent and derivation/attribution concepts; Workflow Run RO-Crate supplies profiles for packaging executable-run provenance. Those existing ideas are reused, not claimed as new. Neither a recorded attribution nor a successful file transfer establishes scientific validity or successful cross-model research.

Primary references reviewed for this design:
- W3C PROV-O: https://www.w3.org/TR/prov-o/
- Workflow Run RO-Crate: https://www.researchobject.org/workflow-run-crate/
- JSON Pointer: https://www.rfc-editor.org/rfc/rfc6901

## Decision

Add `dscc.research/0.1` inside `data.research` of existing seed kinds. Preserve existing canonical encoding, signature domains, artifact kinds and CID bytes. Separate question, literature review, hypothesis, plan, observed evaluation, failure, open question, research state and contribution. Record observable contributor metadata; unknown provider/model/snapshot remains null.

Use existing signed artifacts as primary sources, addressed by CID and JSON Pointer into the signed envelope. All normative CID references become sorted, unique parents; validate pointer resolution before recording and again during handoff. Preserve provenance and observation/interpretation distinctions without generating summaries or silently inferring missing fields. Primary-literature/observation source roles are required where appropriate, but are assertions rather than attestations.

Read a caller-selected ResearchState and its complete bounded ancestor closure. Do not choose a latest state from clocks, overwrite previous states, or resolve conflicting claims by vote. Preserve explicit contradiction/supersession assertions and exact declared-work duplicate candidates alongside originals. Supersession is not deletion or an authority grant. Cross-domain reuse is allowed through input/source links; supersession requires the same research type/project.

The public additive interfaces are CLI `research-record`, `research-handoff` and MCP `record_research`, `get_research_handoff`. This is an extension to `docs/PROTOCOL.md`; all pre-existing interfaces retain their behavior. No new job approval, execution, export-to-file, automatic publication, shell or network permissions are introduced.

## Consequences and open work

T012's local contracts/handoff lane becomes executable. T007's full PROV/RO-Crate export remains separate; this profile is not a serialized PROV ontology or a RO-Crate conformance claim. Source bodies are not replaced with summaries. The seed's limits (32 direct parents, 256-record/8 MiB bundles, small records) remain visible and fail explicitly; large binaries remain external. Namespaced content extensions can preserve domain-specific data but do not silently create executable or dependency semantics.

The experiments that remain necessary are real multi-provider research continuation and measurement of evidence retention, repeated work, contradiction handling and useful subsequent experiments. Synthetic regression fixtures test software contracts only. Public orchestration, fine-grained authorization, model execution and transport still depend on their existing tasks.
