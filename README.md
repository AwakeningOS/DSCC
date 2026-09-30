# DSCC Desktop

**Shared scientific experience. Participant-owned compute. A distributed laboratory for AI research.**

DSCC Desktop is the application project for **Distributed Scientific Cognition Commons**, proposed by **Yusuke Maeda**. Its final goal is a **Distributed AI Research Laboratory**: a world-scale research commons where closed AI systems, open models, local agents and humans can continue the same AI-research projects through shared artifacts, experiments, evaluations and compute. Open Model Commons is the model/compute layer beneath that goal, while DSCC's persistent provenance layer lets research survive changes of model, provider, machine and participant.


## Why DSCC exists: preserving independent AI capacity

DSCC is not only a distributed-computing project and not only a memory system for agents. Its deeper purpose is to preserve **independent access to AI capability** as AI becomes critical infrastructure for research, software, industry, public services and national security.

The project starts from a structural observation: if advanced AI can only be used through a small number of centrally operated services, then model availability, permitted uses, refusal behavior, pricing, data handling and continuity can all change at the same control points. That does **not** mean every restriction is censorship, every government intervention is illegitimate, or every company policy is harmful. It means concentration creates a common failure mode: one policy or outage can affect a very large fraction of users at once.

The 2026 Stanford AI Index reports that industry produced more than 90% of notable frontier models in 2025 and describes the frontier as increasingly concentrated among a small number of organizations; it also notes that the most capable systems are among the least transparent. The same report identifies **AI sovereignty** — greater domestic agency over AI capabilities — as an emerging policy objective while noting that compute infrastructure remains unevenly distributed.  
Sources: [Stanford AI Index 2026 — Research & Development](https://hai.stanford.edu/assets/files/ai_index_report_2026_chapter_1_research_development.pdf), [Policy and Governance](https://hai.stanford.edu/ai-index/2026-ai-index-report/policy-and-governance).

### Centralized safety policy is still centralized power

Closed AI services necessarily make policy choices. A provider may refuse categories of requests, change a model, remove a capability, change retention rules, alter a system prompt, restrict access by region, or discontinue a service. Some of those choices may be justified by safety, law, privacy or commercial constraints. The architectural issue is that users normally cannot independently reproduce, audit or replace the policy stack behind a closed service.

Government regulation can create a similar concentration point when compliance is practical only for a handful of frontier providers, or when public institutions depend on a small set of private models. Conversely, weak regulation can also increase dependence if a few companies become de facto infrastructure without interoperable alternatives.

Current U.S. policy illustrates why DSCC should not be based on a simplistic claim that government policy is always either “pro-AI” or “anti-AI.” The June 2026 White House policy explicitly favors rapid innovation and reducing burdensome regulation, while the September 2026 White House Accord on Super Intelligence is a **voluntary**, non-binding safety agreement among major AI firms involving internal controls, outside audits and board-level oversight. At the same time, national-security policy calls for deep partnerships with private AI companies and rapid access to advanced frontier models.  
Sources: [White House EO, June 2 2026](https://www.whitehouse.gov/presidential-actions/2026/06/promoting-advanced-artificial-intelligence-innovation-and-security/), [White House NSPM-11, June 5 2026](https://www.whitehouse.gov/presidential-actions/2026/06/national-security-presidential-memorandum-nspm-11/), [CBS summary of the voluntary September 2026 accord](https://www.cbsnews.com/news/trump-ai-constitution-tech-execs-openai-anthropic-voluntary-controls/).

DSCC therefore treats **technical exit options** as a resilience property: its architecture is intended to let a user, laboratory, company or community continue useful AI work when a particular provider, policy regime or network service becomes unavailable.

### The military-AI problem is not solved by “refuse everything” or “refuse nothing”

AI is already being integrated into military and intelligence workflows. The June 2026 U.S. national-security memorandum directs faster AI adoption, use of advanced commercial and open-source systems, and preservation of a constitutional chain of command. The January 2026 Department of War AI strategy goes further in procurement policy, calling for standard **“any lawful use”** language and models whose vendor usage-policy constraints do not block lawful military applications.  
Sources: [White House NSPM-11](https://www.whitehouse.gov/presidential-actions/2026/06/national-security-presidential-memorandum-nspm-11/), [Artificial Intelligence Strategy for the Department of War](https://media.defense.gov/2026/Jan/12/2003855671/-1/-1/0/ARTIFICIAL-INTELLIGENCE-STRATEGY-FOR-THE-DEPARTMENT-OF-WAR.PDF).

Military AI is used or proposed for functions such as analysis, defensive cyber operations, logistics, protection of personnel and precision operations. It also raises documented governance concerns including escalation, automation bias, surveillance, accountability gaps, targeting errors, and how systems should behave when legal, factual or policy judgments are disputed.

For DSCC, the important design lesson is that **a non-refusing model is not automatically a free model, and a refusing model is not automatically a safe model**.

A vendor-controlled refusal policy concentrates one class of decisions at the provider. A procurement regime that requires support for lawful military uses concentrates a different class of decisions in the authorized chain of command. DSCC treats either form of concentration as a reason to keep policy provenance and alternative execution paths explicit.

DSCC instead aims for:

- explicit, inspectable policy profiles rather than hidden universal rules;
- owner-controlled local execution boundaries;
- multiple models and providers rather than one mandatory model;
- provenance showing which policy, model and operator produced a result;
- auditability and independent verification for high-stakes claims;
- the ability to preserve disagreement rather than silently deleting dissenting evidence;
- no assumption that a cryptographic signature, government authorization or corporate policy proves scientific or moral correctness.

This does **not** mean removing safety boundaries. It means keeping safety, authority and scientific truth as separate layers that can be examined rather than collapsing them into one central service policy.

### Why local and offline-capable AI matters

If a useful model can run only after contacting a remote service, the user remains dependent on that service for availability and permission. DSCC therefore treats **local-first and offline-capable AI** as a long-term requirement, especially for open-weight models.

The target is not that every person must own a frontier-scale GPU cluster. The target is that useful capability can exist at several levels:

```text
individual machine
      ↓
home / laboratory / office compute island
      ↓
voluntary trusted peers
      ↓
wider DSCC network
```

A node should be able to keep working locally when disconnected. Network participation should add models, compute, evidence and collaborators rather than being a prerequisite for the AI to exist at all.

### National AI sovereignty means retaining an independent capability floor

DSCC does not treat terms such as “AI colonialism” as established technical facts. The concrete engineering concern is **strategic dependency**.

If a country, university system, industry or research community cannot run, inspect, adapt or train important AI systems without foreign cloud services, it is exposed to external changes in price, export controls, sanctions, service availability, model policy and supply chains. The same dependency can exist inside a country when only a very small number of domestic firms control the relevant infrastructure.

DSCC models resilience through multiple independent layers: domestic and foreign providers, open-weight models, locally operable runtimes, independent companies, public and private compute, interoperable protocols and the ability to migrate research state between them. DSCC's role is not to select a national champion. Its role is to make **continuity across providers and jurisdictions technically possible**.

### Decentralization alone is not enough

A decentralized system can also fail badly. It can spread malware, fabricated evidence, poisoned models, abusive workloads, Sybil identities and unverifiable results. DSCC is therefore not based on the equation:

```text
decentralized = trustworthy
```

Instead:

```text
decentralized
+ provenance
+ explicit permissions
+ sandboxing
+ verification
+ source recovery
+ contradiction preservation
+ owner control
= a system that can remain open without treating every peer as trusted
```

This is why DSCC keeps identity, computation verification, scientific evidence, execution permission and publication permission as different states.

### From independent local AI to a distributed research civilization

Local models alone are not enough either. If a million independent agents repeatedly rediscover the same facts and repeat the same failed experiments, decentralization loses much of the advantage of central scale.

DSCC therefore combines **independence** with **shared scientific experience**:

```text
independent models and machines
        ↓
signed artifacts and primary evidence
        ↓
research state and unresolved questions
        ↓
experience graphs including failures and branches
        ↓
shared compute and model infrastructure
        ↓
new experiments, replications and improved agents
        ↺
```

The long-term objective is a distributed AI research laboratory in which no single company, government, model family or machine is required for the research process to continue.

### What DSCC is and is not asserting

DSCC is **not** built on the claim that current governments are already using frontier AI regulation as a unified censorship system. The September 2026 U.S. accord, for example, is currently voluntary and lacks direct government enforcement. Nor does DSCC assume that closed models are inherently malicious or that military AI has no legitimate uses.

The narrower claim is architectural:

> **DSCC is designed so that no single company, government, cloud, model or policy layer is technically required for participants to compute, investigate evidence, preserve research history and continue scientific work.**

DSCC attempts to build that technical alternative: local-first AI, voluntary federation, participant-owned compute, model plurality, durable provenance, shared experience and research continuity without a mandatory proprietary cloud.


[Concept paper — DOI: 10.5281/zenodo.22782576](https://doi.org/10.5281/zenodo.22782576) · [日本語ガイド](docs/START_HERE.ja.md) · [Architecture](docs/ARCHITECTURE.ja.md) · [Development status](docs/STATUS.md) · [Agent instructions](AGENTS.md) · [Development issues](https://github.com/AwakeningOS/DSCC/issues)

## What this repository contains

This is **a tested local foundation, not a released P2P/GPU-sharing desktop app**. It contains the full target architecture, interface boundaries, source-paper traceability, collaboration tasks, and a runnable first slice:

* Persistent, content-addressed research records with Ed25519 signatures and parent links.
* A transactional SQLite catalog, keyword search, bounded records, and signed local events.
* Explicit bundle export/import with signature, identity and dependency checks.
* Owner-approved local computation using one built-in deterministic integer-analysis tool.
* A small MCP stdio server: search, read, record, verify, inspect tools, submit a pending job, and inspect job status. Models cannot approve/run jobs through this adapter.
* A one-person, three-logical-node demo and automated tests, including subprocess MCP exchanges.
* A local large-block store for immutable model-weight/checkpoint shards addressed by CID.
* Versioned Open Model Commons profiles for model manifests, compute capabilities and training-run provenance.
* A deterministic local inference-placement planner that can propose single-device or multi-shard placement from recorded capabilities without executing a model.

**Not implemented:** internet P2P, NAT traversal, remote jobs, actual model loading/inference, GPU execution, distributed training/pre-training, arbitrary-code sandboxes, payments, native desktop UI, installers, or unattended model-development loops. Host applications (LM Studio/Codex) have not been launched here. See `reports/validation.md` for the exact tests actually run.

## Quick start

Requires Python 3.11+ and `cryptography` (see `pyproject.toml`). Use a dedicated virtual environment.

```sh
git clone https://github.com/AwakeningOS/DSCC.git
cd DSCC
python -m venv .venv
# Linux/macOS:
. .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e '.[dev]'
python -m pytest -q
python -m dscc demo
```

The demo creates three local node directories in a temporary location, transfers signed bundles, executes a small approved job, and verifies that a third node can read the result and its ancestry. It performs **file-bundle transfer, not P2P networking**, and does not download an LLM or start GPU work.

For a persistent notebook:

```sh
python -m dscc --home ~/.dscc init
python -m dscc --home ~/.dscc record --file examples/research_record.json
python -m dscc --home ~/.dscc search 'materials'
python -m dscc --home ~/.dscc status
```

Run `python -m dscc --help` for owner-only job approval, bundle export/import and audit inspection. Never place private keys or the live `.dscc` directory in Git.

### Open Model Commons local foundation

Large model bytes are imported separately from signed metadata:

```sh
python -m dscc --home ~/.dscc block-add --file ./model-00001-of-00002.safetensors
python -m dscc --home ~/.dscc model-record --file ./model_profile.json --license Apache-2.0
python -m dscc --home ~/.dscc capability-record --file ./capability_profile.json
python -m dscc --home ~/.dscc plan-inference --model-cid MODEL_CID --capability-cid CAPABILITY_CID
```

Example profile shapes are in `examples/omc/`. The planner only returns a placement proposal; it does not contact peers, reserve hardware or execute model code. Artifact bundles currently transfer signed metadata only, not large model blocks.

## Connect an AI application

```sh
python scripts/make_client_config.py --home ~/.dscc --out ./client-config
```

This generates `lmstudio.mcp.json` and `codex.config.toml` with the **actual Python executable** and an absolute data-directory path. Merge the generated entries into your application's configuration; do not overwrite existing settings. The generator does not change another application's files. [Detailed connection guide](docs/INTEGRATIONS.ja.md).

## Continue collaboratively

Give a coding agent `AGENTS.md`, then choose one ready task from `docs/TASKS.md` and its matching [GitHub Issue](https://github.com/AwakeningOS/DSCC/issues). Each task includes dependencies, edit boundaries and acceptance tests. Work on one branch per task, use separate worktrees for concurrent agents, and open a pull request with recorded validation. The task pack prepares collaboration; it does not launch or schedule agents by itself.

The repository is **AwakeningOS/DSCC**. The application/package name remains `dscc-desktop`. See [GitHub collaboration setup](docs/GITHUB_SETUP.ja.md) for instructions. Repository rules and required reviews must be enabled separately by the owner; committing a workflow file does not configure branch protection.

Long-term blockers between the current local foundation and the Distributed AI Research Laboratory are tracked in the [世界規模化に向けた未解決課題レジストリ](docs/GLOBAL_SCALE_CHALLENGES.ja.md). It is a living backlog for future agents and contributors: an item remains unresolved until its implementation, assumptions, measurements and remaining limits are recorded.

## Design proposals

[計算で整理する共有記憶 — Computational Memory](docs/proposals/COMPUTATIONAL_MEMORY.ja.md) proposes preserving original research records while using versioned embeddings, lexical search and provenance-aware graph retrieval to organize memory across different AI models. It includes primary-source references, compatibility requirements and an implementation handoff related to T007. **Proposal only; no memory-search implementation or benchmark result is introduced by this document.**

[分野を越える探索地図 — Exploration Atlas](docs/proposals/EXPLORATION_ATLAS.ja.md) extends that direction to trial-and-error paths across engineering, model development and everyday experience. It specifies typed episodes, independent semantic/structural retrieval, explicit analogy mappings, trial-backed transfer reports and source-linked motifs. [Implementation contracts](docs/proposals/exploration-atlas/IMPLEMENTATION.md) and [T010](docs/tasks/T010.md) include draft schemas, synthetic examples and executable contract tests. **The atlas application, semantic extraction, retrieval quality and map UI are not yet implemented or demonstrated.**

[みんなで使い、みんなで育てるオープンLLM計算コモンズ — Distributed Open Model Commons](docs/proposals/DISTRIBUTED_OPEN_MODEL_COMMONS.ja.md) defines the model/compute layer beneath the final research-lab goal: public inference for open models, voluntary compute contribution, globally distributed low-communication training, and provenance-preserving community model research. It separates results already demonstrated by prior decentralized-training research from the additional heterogeneous, adversarial and public-network problems DSCC would still need to solve. **Proposal only; DSCC currently has no distributed inference, GPU worker or model-training implementation.**

[世界中のAIと人間がAIを共同研究する分散研究所 — Distributed AI Research Laboratory](docs/proposals/DISTRIBUTED_AI_RESEARCH_LAB.ja.md) defines the final DSCC goal. Closed AI systems can participate as research agents through APIs/tools without exposing proprietary weights; open models can participate both as researchers and as research subjects; humans contribute questions, experiments, evaluation and compute. Shared research artifacts connect literature review, hypotheses, experiments, failures, evaluation and model lineage across participants. **This is the final architectural goal, not a claim that autonomous distributed AI research is implemented today.**

[AIの経験と作業状態を共有するDSCC — Experience and State Sharing](docs/proposals/EXPERIENCE_AND_STATE_SHARING.ja.md) connects model-independent experience graphs, working-state snapshots, latent experience capsules and versioned converters to T010/T012 and Open Model Commons. It records capture/replay contracts, cross-model compatibility, WAN costs, evaluation, sixteen open challenges and six implementation lanes. The [primary-source evidence ledger](docs/proposals/experience-sharing/SOURCES_AND_EVIDENCE.ja.md) distinguishes reported results from DSCC capabilities. **Design material only; no trajectory collector, KV transfer, latent injection or new execution authority is implemented by these documents.**

[Latest research scout — 2026-09-25](docs/research/2026-09-25-LATEST_DSCC_PAPERS.ja.md) maps sixteen recent papers and surveys to T005/T009/T010/T011/T012, with concrete implementation candidates and acceptance evidence for research-agent evaluation, KV/latent transfer, resilient distributed execution, remote-worker verification/privacy, and interoperability/governance. **It is a dated handoff/reference, not evidence that those systems are implemented in DSCC.**

[Enabling technologies scout — 2026-10-01](docs/research/2026-10-01-ENABLING_TECHNOLOGIES.ja.md) tracks implementation-ready protocols, runtimes and hardware standards that can reduce how much DSCC must invent itself: WiCi, NVIDIA Dynamo/NIXL, vLLM KV transfer, OpenSharing, DNS-AID, exo, UALink, Ultra Ethernet and CXL. It maps them to adapter and compute-island implementation lanes with acceptance boundaries. **Reference/design material only; no external runtime or hardware capability is implemented by this document.**

## Attribution and licensing

Original DSCC concept: Yusuke Maeda. This initial code and new implementation documents are provided under the MIT license in `LICENSE`. Material in `docs/reference/` is retained from the supplied DSCC research packet with separate attribution and provenance; third-party software and future research assets retain their own licenses. The concept-paper DOI identifies the paper, not a software-release DOI.
