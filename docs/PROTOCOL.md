# DSCC seed protocol 0.1

This document describes the runnable local implementation, not the entire DSCC paper protocol. Adapters must preserve these versioned contracts or introduce an explicit migration. The source paper's richer schemas are retained separately in `docs/reference/original_schemas/`.

## 1. Canonical metadata and identifiers

Allowed metadata consists of objects with string keys, arrays, strings, integers between `-(2^53-1)` and `2^53-1`, booleans and null. Strings must already be NFC normalized and contain no lone surrogates. Nesting is bounded at 32. Object keys sort by UTF-16 code units; JSON is UTF-8 without whitespace. Duplicate keys and nonfinite numbers are rejected when decoding. Floats are rejected when canonicalizing; represent decimal metrics as strings with explicit units in this seed. Large scientific arrays and complete binary/CAR support are a later adapter, not a requirement to convert arrays to prose.

This is a restricted interoperable JSON domain, not a claim to implement RFC 8785 for all JSON numbers. `schemas/test_vectors.json` contains stable vectors. Re-encoding can never silently round a submitted scientific number.

Identifiers are real **CIDv1/raw/sha2-256**, base32 lowercase: version `0x01`, codec `0x55`, multihash `0x12 0x20`, then the 32-byte SHA-256 digest. There is one signed JSON envelope per raw block, at most 1 MiB. This does not implement IPFS transport, a UnixFS file tree, CAR archives, or dag-cbor. A normal `ipfs add` file may receive a different CID. Future adapters must retain the encoded bytes and codec rather than rename SHA digests as arbitrary CIDs.

## 2. Artifact envelope

The body is validated by `schemas/artifact.schema.json` and runtime checks:

```json
{"schema":"dscc.artifact.seed/0.1","kind":"MemoryCapsule","title":"Example","summary":"","data":{"open_questions":["Which condition should be tested next?"]},"parents":[],"license":"NOASSERTION"}
```

The envelope contains exactly `body`, `public_key` (64 lowercase hex characters), and `signature` (base64 Ed25519 signature). The signed message is `DSCC-ARTIFACT-SEED-v1\0` concatenated with canonical body bytes. The CID hashes the entire canonical signed envelope. Identical signed envelopes deduplicate; the same body signed by another key has a different CID. Signatures identify keys, not verified real-world identities or scientific truth.

All 14 paper object kinds are recognized as labels. Their rich, kind-specific semantics are not yet implemented. A `CreditReceipt` record creates no balance or financial entitlement. A `VerificationReceipt` label does not turn a claim into verified science. The local input set is restricted to small records, not complete model checkpoints.

Parents are at most 32 unique CIDs and must be present and valid before insertion. Timestamps are stored in catalog/events rather than added to the substantive artifact body. A `MemoryCapsule` contains reviewable results, evidence, reasoning summaries and open questions; hidden model chain of thought is not required.

## 3. Local storage and events

`catalog.sqlite3` holds immutable signed envelope bytes and rebuildable metadata in separate columns. Large immutable binary payloads such as model-weight shards use a separate local `blocks/raw/` store keyed by the same CIDv1/raw/sha2-256 profile. Large blocks are not signed artifacts by themselves; signed manifests reference their CIDs, sizes, formats and provenance. Every artifact read verifies its CID, canonical encoding, signature and manifest. Every explicit block verification re-hashes the stored bytes. Keyword-search hits are metadata hints and are revalidated on fetch.

Writes use SQLite `BEGIN IMMEDIATE` transactions. Artifact insertion and event insertion commit atomically. Events use the separate `DSCC-EVENT-SEED-v1\0` signature domain and a previous-event CID, sequence number, timestamp, event name and structured data. Audit verifies the chain currently retained. It cannot detect deletion of an entire history tail without an independently retained head, and cannot protect against an attacker controlling the same OS account and signing key.

There are limits of 10,000 artifacts and 10,000 jobs. The metadata quota counts logical envelope/event/specification bytes. A separate configured block quota counts stored large-block payload bytes before import. Neither is a complete filesystem, RAM, CPU, GPU or power quota: filesystem metadata, SQLite pages/journals and temporary operating-system behavior can exceed the reported logical values. Restore capacity before attempting job recovery after storage exhaustion. No background cleanup, replication, remote pinning or retention guarantee is implemented.

## 4. Explicit bundle exchange

Export is an owner CLI operation. It creates a JSON bundle with `schema: dscc.bundle.seed/0.1`, `root` and `artifacts: [{cid, envelope}, ...]`. The bundle contains exactly the root and its transitive parents: at most 256 records and 8 MiB. It contains no private key, credentials, live database, jobs or audit database. Export includes all ancestor content, so an owner must inspect confidentiality and licensing before sending it.

Import accepts only signatures belonging to the importing node or the owner-supplied trust-key set. It rejects altered content, duplicate CIDs, missing parents and unrelated hidden extra records. Validation precedes a transactional topological insert, so a rejected bundle does not partially enter the store. Imported content is never executed. Requiring an explicitly trusted key limits accidental intake, but a trusted signer can still publish false or harmful research content.

File exchange is not P2P networking. Seed artifact bundles do **not** embed Open Model Commons large blocks; model manifests may therefore import with missing local weight CIDs. The future peer transport reuses immutable-byte checks while adding authenticated peers, consent scopes, bandwidth limits, chunked large-block transport, resume, availability/repair, disconnect handling and explicit publication.

## 5. Local computation

`schemas/job.schema.json` describes the seed's only job: `dscc.integer_stats.v1` over a Dataset CID. Input has 1–10,000 integers, each bounded to ±1,000,000,000. Booleans are not integers. Admission validates data; execution computes count, sum, minimum and maximum.

The `tool_digest` currently hashes the **semantic tool descriptor**, not the executable's complete source/dependency closure. It is not a supply-chain attestation. This is acceptable only for the one trusted function installed alongside the app. Remote tools require pinned executable bytes, dependency/environment manifests and independent validation before their runtime is enabled.

State transitions are `pending -> approved -> running -> succeeded/failed`. An owner can cancel a pending/approved job. After checking no worker is active, an owner can explicitly recover an interrupted running job to failed. A result is committed only while the job is running, and duplicate execution of a completed job is rejected. No exactly-once distributed execution is claimed. Normal process termination remains the way to stop the short built-in runner immediately; runtime-level cancellation is a future capability.

The output is an ExperimentRun with the Dataset as a parent, tool descriptor, result, and explicit `independent_scientific_verification: false`. This is a local deterministic example, not a general Python execution service, an isolated sandbox or a GPU worker.

## 6. MCP stdio subset

The client launches `python -m dscc --home ABSOLUTE_PATH mcp`. UTF-8, newline-delimited JSON-RPC 2.0 is read from stdin; only protocol messages are written to stdout. Errors go to stderr. Maximum inbound message is 1 MiB. Initialization supports protocol dates `2025-11-25` and `2025-06-18`; a different client version is offered the first version and the client decides compatibility. An `initialized` notification completes negotiation.

Implemented methods: `initialize`, `ping`, `tools/list`, `tools/call`, `resources/list`, `resources/read`. No subscriptions, elicitation, sampling, HTTP transport, OAuth or long-running MCP Tasks are advertised. Unknown request methods receive -32601. Tool errors use `isError: true`. The seed adapter is not the official MCP SDK and host interoperability remains unverified until T002.

| Tool | Effect |
|---|---|
| node_status | Read capability flags and logical payload usage |
| search_assets | Bounded literal keyword query over local metadata |
| fetch_artifact | Verify and read one record |
| record_artifact | Sign and persist one local record, without publication |
| verify_artifact | Check CID, signature and direct-parent availability |
| inspect_tools | Return the built-in tool contract |
| submit_job | Create a pending job only |
| job_status | Read a job specification/state |
| record_open_model | Validate and store a local OMC model manifest; does not upload weights or execute a model |
| inspect_open_model | Read an OMC model manifest and report local weight-block availability |
| record_compute_capability | Store an owner-signed capability/policy record; does not publish or authorize remote execution |
| record_training_run | Store a training observation; does not start training |
| plan_open_model_inference | Create a deterministic non-executing placement proposal from model/capability records |

There is no MCP tool for owner approval, execution, export, key management, large-block upload, resource-policy activation or remote publication. However, the MCP process runs as the same OS user in M0 and loads the node key. An agent with a separate unrestricted shell can bypass interface-level distinctions. Strong owner/agent/process separation is T001, not a feature of this seed.

Resources use `dscc://artifact/{cid}`. Resource listing is CID-ordered in pages of 100 and uses the last CID as a cursor. It is not a snapshot under concurrent writes; restart listing for a complete current view. Keyword search returns up to its requested limit (maximum 100). Access to a project means access to all of that node's research records; use separate node directories for confidentiality boundaries until finer-grained authorization is implemented.

## 7. Open Model Commons local foundation

The OMC foundation follows ADR-0004 and keeps the existing seed artifact kinds and signed-envelope bytes unchanged. It adds three versioned payload profiles:

- `dscc.omc.model/0.1` in `MemoryCapsule.data.omc_model`.
- `dscc.omc.capability/0.1` in `PolicyProfile.data.omc_capability`.
- `dscc.omc.training-run/0.1` in `ExperimentRun.data.omc_training_run`.

A model profile contains architecture/tokenizer identity, immutable weight-block references, runtime requirements and artifact provenance. Weight blocks may be locally absent; `model-inspect` reports that condition instead of pretending a complete model copy exists.

A capability profile records devices, usable-memory claims, supported precisions/runtime tags, coarse network measurements and owner policy. It is a signed statement by the local node, not a hardware attestation, benchmark proof, peer-discovery record or promise of current availability.

A training-run profile records a parent model, dataset/code/capability artifact CIDs, method, token count, state, metrics and checkpoint-block references. Recording such a profile is provenance only. The foundation contains no trainer and never converts a recorded `succeeded` field into proof that DSCC executed or verified the training.

The local inference planner consumes one model profile and explicit capability-record CIDs. It may propose a single-device replica or shard placement across compatible GPUs. Its output always records `execution_authorized: false` and `network_execution: false`. The planner does not contact peers, reserve devices, inspect real GPU state, load model code, move tensors or benchmark WAN latency.

## 8. Extension contracts

A peer adapter transfers immutable encoded blocks and signed manifests; it cannot alter local policy. A runtime adapter consumes admitted jobs and returns execution observations, not authoritative scientific truth. A verifier emits method/evidence/limits. A catalog adapter provides disposable search hints. A desktop UI requests owner actions over authenticated local IPC. MCP remains one client of the application service, not the service's authority model.

Protocol changes require test vectors, migration behavior and an ADR. The original DSCC goals remain broader than this seed: artifact reuse, voluntary compute, shared experimental worlds, and continuity across different models.
