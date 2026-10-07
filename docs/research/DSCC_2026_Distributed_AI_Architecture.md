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

## 2. Decentralized GPU Mesh Training

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

## 3. Adaptive Synchronization Training

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

## 4. Elastic Compute Sharing

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

## 5. Evidence Lineage and Epistemic Sybil Resistance

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

## 6. Byzantine Placement Testing

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

### Phase 1 — establish the training/provenance substrate

- artifact evidence lineage
- node capability metadata
- explicit training-run and update provenance
- adaptive synchronization parameters

### Phase 2 — dynamic participant-owned compute

- elastic compute scheduler
- P2P checkpoint/state transfer
- dynamic membership and failure recovery
- heterogeneous-node placement

### Phase 3 — adversarially robust global training

- Byzantine placement simulator
- malicious-update detection / robust aggregation
- Sybil-resistant contribution accounting
- verifiable useful-compute mechanisms
- removal or replication of mandatory central coordination services

### Phase 4 — heterogeneous decentralized model execution

- decentralized GPU mesh training protocol
- pipeline/model partitioning across heterogeneous devices
- low-bandwidth activation transfer and correction mechanisms

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
