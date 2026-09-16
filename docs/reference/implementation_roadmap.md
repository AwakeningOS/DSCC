# DSCC Implementation Roadmap v0.1

## Phase 0: Protocol and schemas

Deliverables:
- Artifact, Job, Node Capability JSON Schemas
- RO-Crate profile
- PROV mapping
- CID canonicalization profile
- Verification class specification
- Tool manifest profile
- test vectors

Exit criteria:
- Two independent implementations generate the same CID for the same canonical bundle.
- Schemas validate public examples.
- Provenance graph can reconstruct all inputs and tool digests.

## Phase 1: Trusted federation prototype

Components:
- Kubo/IPFS storage
- libp2p peer discovery
- SQLite local catalog
- signed append-only event log
- MCP server for local LLMs
- CWL runner
- WASM and OCI/gVisor executor
- simple resource scheduler
- V0/V1 verification
- web dashboard

Exit criteria:
- 3-10 nodes complete an end-to-end experiment.
- One node can disappear without losing project state.
- A new model can resume a project from its assets.
- Third-party re-execution reproduces a deterministic result.

## Phase 2: Community network

Components:
- federated signed indexes
- semantic search
- reputation and credit receipts
- multiple pinning policies
- public tool registry
- revocation and transparency
- adaptive verification
- A2A delegation

Exit criteria:
- 100-node emulation or real network.
- Search remains usable with malicious index records.
- New nodes cannot gain high trust without validated work.
- Job completion remains robust under churn.

## Phase 3: Adversarial verification

Components:
- randomized auditors
- diversity-aware replica selection
- Byzantine aggregation
- statistical verification for V2
- artifact prompt-injection defenses
- stronger Sybil costs
- privacy classification

Exit criteria:
- Predefined malicious-worker scenarios are detected at measured rates.
- Credit fraud is bounded.
- Colluding nodes cannot dominate a project under the tested assumptions.

## Phase 4: Confidential science

Components:
- encrypted artifacts
- organization credentials
- confidential containers
- remote attestation
- regional scheduling
- output disclosure policies
- audit exports

Exit criteria:
- Sensitive inputs remain hidden from host administrators under the selected TEE threat model.
- Public outputs retain verifiable provenance without exposing raw data.

## Phase 5: Cross-domain scientific commons

Components:
- domain profiles
- ontology bridges
- world snapshot interoperability
- claim/evidence federation
- public reproducibility campaigns
- long-term archival partners

The roadmap intentionally does not require a cryptocurrency, a single global DAO, or a monolithic shared model.
