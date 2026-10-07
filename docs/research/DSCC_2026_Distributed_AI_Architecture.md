# DSCC 2026 Distributed AI Architecture Research Notes

## Purpose

This document collects research directions that may affect DSCC architecture decisions. It is reference material, not a direct implementation specification.

The notes distinguish between:

- capabilities already demonstrated in published systems;
- techniques that appear transferable to DSCC;
- unresolved requirements that remain before participant-owned, permissionless and adversarially robust distributed training is possible.

## 1. Foundational Prior Art: INTELLECT-1 and Prime

### Reference

- **INTELLECT-1 Technical Report** — Sami Jaghouar et al., Prime Intellect et al., arXiv:2412.01152v1, 2024-12-02  
  https://arxiv.org/abs/2412.01152
- Prime distributed-training framework  
  https://github.com/PrimeIntellect-ai/prime

### Why this matters for DSCC

INTELLECT-1 is an important existence proof for globally distributed pre-training rather than merely a proposal for it.

The reported run trained a **10B-parameter model from pre-training over 1 trillion tokens**, using:

- up to **14 concurrent nodes**;
- up to **112 H100 GPUs**;
- **30 independent compute providers**;
- nodes distributed across **five countries and three continents**;
- dynamic node joins and departures during the run;
- **83-96% compute utilization**, depending on geographic distribution.

This means the following architecture has already been demonstrated at meaningful scale:

```
independent compute providers
        ↓
geographically distributed GPU nodes
        ↓
low-frequency global synchronization
        ↓
shared model training state
        ↓
one continuously trained foundation model
```

For DSCC, INTELLECT-1 should therefore be treated as a baseline prior art system for distributed pre-training, not as a speculative future direction.

### Communication strategy

Prime combines:

- **FSDP inside a node**, where high-bandwidth local GPU interconnects are available;
- **DiLoCo across nodes**, where ordinary Internet bandwidth is the bottleneck;
- **int8 pseudo-gradient transmission** with fp32 accumulation.

Workers perform many local optimizer steps before a global outer-optimizer synchronization.

The report states that the deployed INTELLECT-1 configuration reduced communication by roughly **400x** relative to conventional data-parallel synchronization. It also discusses configurations reaching up to roughly **2000x communication-volume reduction** by combining int8 pseudo-gradient transmission with synchronization every 500 local steps.

Architectural lesson for DSCC:

```
do not attempt to reproduce datacenter networking over the Internet
                ↓
reduce how often global communication is required
                +
compress what must cross the wide-area network
```

### Dynamic membership and fault tolerance

Prime includes an `ElasticDeviceMesh` for nodes that may join or leave while training continues.

New nodes synchronize model and optimizer state using **peer-to-peer checkpoint transfer** from an active participant rather than requiring all training state to come from centralized object storage.

Two modes are described:

- non-blocking checkpoint synchronization while existing nodes keep training;
- blocking synchronization, where active nodes pause briefly while a new node obtains the checkpoint.

The production run used the more conservative blocking approach; reported peer-to-peer checkpoint transfers generally took about **30-60 minutes**.

Nodes are monitored through heartbeats. Failed or departed nodes can be removed from the process group and collective operations retried with the remaining participants.

This is directly relevant to DSCC's volunteer-compute model:

```
node membership != fixed cluster membership

participants may:
join
leave
fail
return
change capacity
```

Training infrastructure must treat membership as dynamic state.

### What DSCC can reuse conceptually

The strongest reusable ideas are:

1. **local-fast / global-slow parallelism**
   - exploit fast links only inside each physical node or trusted compute island;
   - minimize wide-area synchronization.

2. **Local-SGD / DiLoCo-style outer synchronization**
   - make global synchronization a sparse event rather than a per-step requirement.

3. **P2P state acquisition**
   - a new participant should be able to obtain current training state from existing peers.

4. **dynamic process groups**
   - training membership must tolerate changing world size.

5. **explicit fault detection and retry**
   - node disappearance must be a normal operating condition rather than a fatal exception.

### What INTELLECT-1 does not solve for DSCC

INTELLECT-1 is not yet the full DSCC target.

Important gaps include:

- the compute was largely homogeneous, high-end H100 infrastructure rather than arbitrary consumer GPUs;
- the system used a **master key-value store** for coordination;
- the training network was not an open, permissionless adversarial network;
- the report does not solve Byzantine or Sybil participants sending malicious training updates;
- participant identity, payment, reputation and proof-of-computation remain separate problems;
- distributed data governance and adversarial dataset poisoning remain unresolved;
- the implementation primarily exploits the flexibility of data-parallel training, while highly heterogeneous model/pipeline partitioning remains harder;
- checkpoint propagation moves model and optimizer state, but does not itself provide DSCC-style persistent research provenance, experience graphs or independent evidence lineage.

Therefore DSCC should not reproduce Prime unchanged. It should treat it as the current empirical lower bound for what a practical global training system must at least match.

### DSCC research questions created by this prior art

INTELLECT-1 narrows DSCC's open research problem from:

```
Can globally distributed pre-training work at all?
```

to:

```
Can it work with:
- heterogeneous participant-owned GPUs;
- permissionless or semi-permissionless membership;
- adversarial / Byzantine nodes;
- independent verification of useful compute;
- dynamic bandwidth and availability;
- decentralized coordination without a single mandatory control service;
- durable provenance connecting model updates to data, experiments and contributors?
```

That distinction is important: DSCC should not spend research effort re-proving the part INTELLECT-1 has already demonstrated.

## 2. Deployment Strategy: Start with a Trusted Volunteer Compute Cooperative

A practical DSCC path does not require solving the hardest permissionless-adversarial problem before distributed training can begin.

There is a useful intermediate regime:

```
participants share a common goal
        +
participants voluntarily contribute compute
        +
nodes are mostly honest
        +
nodes are still unreliable, heterogeneous and temporary
```

This should be treated as a first-class deployment target rather than as a temporary shortcut.

A plausible early constituency is the local/open-model community: people who want independent, locally operable AI capability and may therefore be willing to contribute idle GPUs to a shared training effort. Concern about future restrictions can strengthen that coordination incentive, but DSCC should not assume that any particular regulation is inevitable. The engineering point is broader: **shared interest can substitute for a fully open anonymous market during the first deployment stage.**

### Threat model for the first stage

The first training network can reasonably target **honest-but-unreliable** participants:

- nodes may disconnect without notice;
- bandwidth may fluctuate;
- GPUs may differ greatly in speed and VRAM;
- nodes may return after long absences;
- a participant may reclaim their machine at any time;
- a node may fail accidentally;
- participants are not assumed to be actively poisoning updates.

This changes the initial priority order.

For the first practical system, DSCC should prioritize:

1. **churn tolerance**;
2. **heterogeneous GPU scheduling**;
3. **checkpoint/state replication**;
4. **fast rejoin and catch-up**;
5. **bandwidth-adaptive synchronization**;
6. **training continuity as world size changes**.

Byzantine robustness and Sybil resistance remain essential for later open participation, but they should not block the trusted-volunteer milestone.

### What "full churn tolerance" should mean

No distributed system can continue if every copy of the current state disappears simultaneously.

Therefore the useful target is not literally "survive loss of every node." It is:

> **Any individual worker, and any ordinary subset of workers, may leave without terminating the training run, provided enough replicated state and compute remain available.**

A minimal design target is:

```
worker A ─ training
worker B ─ training
worker C ─ training
worker D ─ checkpoint/state replica

        ↓ worker B leaves

worker A ─ training
worker C ─ training
worker D ─ promoted / catches up
```

Current checkpoints and essential optimizer/training state should exist on multiple independent participants and, when appropriate, durable storage.

A worker that returns later should be able to:

```
discover current run
      ↓
fetch authenticated current state
      ↓
validate ancestry / training-run provenance
      ↓
catch up
      ↓
rejoin without restarting the run
```

### Staged trust model

DSCC should separate three deployment stages.

#### Stage 1 — Trusted Compute Cooperative

Participants are invited, registered, or otherwise known to the project.

Primary problems:

- churn;
- heterogeneous hardware;
- bandwidth asymmetry;
- checkpoint replication;
- dynamic membership;
- contribution measurement.

This stage is the closest extension of INTELLECT-1 toward participant-owned local GPUs.

#### Stage 2 — Open Cooperative

New participants may join, but identity, reputation and quarantine mechanisms exist.

Additional problems:

- suspicious-update detection;
- contribution verification;
- reputation;
- update isolation;
- rollback / exclusion;
- stronger provenance.

#### Stage 3 — Permissionless DSCC

Anyone may attempt to participate.

Additional problems become mandatory:

- Byzantine-resilient aggregation;
- Sybil resistance;
- proof or verification of useful compute;
- poisoning resistance;
- adversarial topology testing;
- decentralized coordination without a single trusted operator.

This staged model avoids a research trap:

```
permissionless Byzantine problem unsolved
        ↓
therefore no distributed training deployment
```

Instead:

```
trusted volunteer federation
        ↓
working heterogeneous global training
        ↓
open cooperative
        ↓
permissionless adversarially robust network
```

### Recruitment is part of the systems design

For DSCC, compute acquisition need not begin as a purely anonymous marketplace.

A shared objective can itself recruit compute:

```
people want independent local/open AI capability
        ↓
participants contribute idle GPUs
        ↓
the network trains a shared model
        ↓
contributors receive access, attribution, reputation,
or other project-defined benefits
```

This is technically important because it allows the first distributed-training network to optimize around cooperation rather than immediately paying the full complexity cost of anonymous adversarial participation.

## 3. Decentralized GPU Mesh Training

### Core idea

Recent decentralized GPU mesh training work explores running LLM adaptation over heterogeneous GPU nodes connected by limited bandwidth networks.

Important architectural lesson:

```
Do not assume high-speed datacenter networking.
Adapt the training algorithm to unreliable distributed resources.
```

Potential DSCC integration:

- activation/gradient compression layers
- low-bandwidth worker protocols
- correction or verification paths for compressed communication
- capability-aware placement

Candidate node metadata:

```json
{
  "gpu": "",
  "vram": "",
  "bandwidth": "",
  "latency": "",
  "availability_window": "",
  "trust_score": ""
}
```

## 4. Adaptive Synchronization Training

Fixed synchronization intervals are inefficient when worker quality and network conditions change.

Future DSCC training scheduler should consider:

```
H(t)=f(loss_state, bandwidth, latency, node_stability)
```

instead of a fixed local-step interval.

Possible extension:

- unstable volunteer nodes synchronize less frequently
- stable high-performance nodes contribute more often
- checkpoint frequency adapts to interruption probability

INTELLECT-1 demonstrates that sparse outer synchronization is practical at global scale; adaptive-synchronization work suggests that DSCC should go further and make the interval itself responsive to training and network state.

## 5. Elastic Compute Sharing

Distributed compute should be modeled as time-dependent availability.

A node is not simply:

```
online / offline
```

but:

```
compute_capacity(t)
```

Suggested metadata:

```json
{
 "expected_idle_time": "",
 "interrupt_probability": "",
 "checkpoint_frequency": ""
}
```

INTELLECT-1's dynamic join/leave support provides a concrete precedent for treating membership changes as a routine training event. DSCC extends that requirement to finer-grained participant-owned compute whose availability may change much more frequently.

## 6. Evidence Lineage and Epistemic Sybil Resistance

DSCC shares research artifacts and agent experiences. Identity count alone is not enough to measure independent evidence.

Example failure:

```
one source
  -> many agents
  -> many identical conclusions
```

Required provenance fields:

```json
{
 "artifact_id": "",
 "evidence_root_id": "",
 "parent_artifacts": [],
 "producer_node": "",
 "model_id": "",
 "source_ids": []
}
```

Agent count must not be confused with independent knowledge.

For distributed training, the same principle should eventually extend to update provenance:

```
training update
  -> contributing node
  -> checkpoint/model parent
  -> data or data shard
  -> optimizer/training state
  -> verification result
```

A model update should not become trusted merely because many identities repeat or relay it.

## 7. Byzantine Placement Testing

Security testing should not only measure malicious node percentage.

Important question:

```
Where are malicious nodes placed in the network graph?
```

DSCC security benchmarks should include:

- random Byzantine placement
- worst-case topology placement
- clustered Sybil nodes
- influence propagation tests

This becomes especially important when extending INTELLECT-1-style dynamic global training from trusted compute contributors to a broader DSCC network.

## Recommended implementation priority

### Phase 1 — trusted volunteer training substrate

Goal: make a cooperative network of participant-owned GPUs able to keep one training run alive despite ordinary churn.

- artifact evidence lineage
- node capability metadata
- explicit training-run and update provenance
- P2P checkpoint/state transfer
- replicated current-state availability
- dynamic membership and failure recovery
- heterogeneous-node placement
- adaptive synchronization parameters
- elastic compute scheduler
- rejoin / catch-up protocol

### Phase 2 — heterogeneous decentralized model execution

- decentralized GPU mesh training protocol
- pipeline/model partitioning across heterogeneous devices
- low-bandwidth activation transfer and correction mechanisms
- consumer-GPU-aware placement and memory planning

### Phase 3 — open cooperative hardening

- suspicious-update detection
- quarantine and rollback
- contribution verification
- identity / reputation integration
- stronger update provenance

### Phase 4 — permissionless adversarial robustness

- Byzantine placement simulator
- malicious-update detection / robust aggregation
- Sybil-resistant contribution accounting
- verifiable useful-compute mechanisms
- poisoning resistance
- removal or replication of mandatory central coordination services

## Architectural direction

The combined lesson from INTELLECT-1 and newer work is not merely that decentralized training may become possible.

A substantial part is already possible.

The remaining design problem is to move from:

```
globally distributed but coordinated and mostly trusted training
```

toward:

```
participant-owned
heterogeneous
dynamic
verifiable
adversarially robust
and progressively decentralized training
```

The common trend across these studies is:

```
remove heterogeneity
```

is becoming less realistic.

The emerging approach is:

```
accept heterogeneous resources
and adapt the system around them.
```

This matches DSCC's goal of participant-owned compute, persistent provenance and distributed research continuity.
