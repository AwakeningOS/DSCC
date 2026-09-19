# ADR-0004 — Open Model Commons profiles and large-block separation

Status: adopted for the local foundation.

## Context

The long-term Distributed Open Model Commons goal needs model checkpoints, compute-capability descriptions and training provenance without pretending that the current seed can already perform distributed inference or training. Existing signed seed artifacts are limited to small JSON records and their CIDs must remain stable.

## Decision

1. Keep the existing 14 seed artifact kinds and signed-envelope format unchanged.
2. Add versioned Open Model Commons payload profiles inside existing kinds:
   - `MemoryCapsule.data.omc_model` for a model manifest.
   - `PolicyProfile.data.omc_capability` for an owner-signed compute-capability record.
   - `ExperimentRun.data.omc_training_run` for a recorded training observation.
3. Store large immutable binary data such as weight shards in a separate local raw block store. Each block uses the same CIDv1/raw/sha2-256 identifier profile, but it is not a signed research artifact by itself.
4. A model manifest references weight blocks by CID, byte length, format and shard name. The signed manifest carries model identity, runtime requirements, provenance and license context.
5. The seed JSON artifact bundle continues to contain artifacts only. It does not silently embed large blocks. A later transport must define chunked large-block exchange, availability and repair.
6. Compute-capability records are advertisements and owner policy statements, not proof that a remote GPU exists or is currently available.
7. The local inference planner creates a deterministic placement proposal only. It does not contact peers, allocate devices, authorize jobs, load model code or execute inference.
8. MCP may record and inspect OMC metadata and create non-executing plans, but large block upload remains an owner CLI action. No MCP tool may approve or launch distributed model execution in this foundation.

## Consequences

Old artifacts, CIDs and bundles remain valid. A future full OMC implementation can replace the local block adapter and planner behind explicit interfaces without rewriting signed model manifests.

The first implementation intentionally solves OMC-0 contracts and local planning, not OMC-1 distributed inference. GPU isolation, peer transport, runtime execution, verification, privacy and distributed training remain separately gated work.
