# DSCC Desktop

**Local AI. Shared scientific experience. Participant-owned compute.**

DSCC Desktop is the application project for **Distributed Scientific Cognition Commons**, proposed by **Yusuke Maeda**. The target product lets a person connect a local AI application, select research assets to share, and contribute explicitly authorized storage or computation. Models and computers may change while research artifacts remain reusable. The long-term Open Model Commons direction also treats open-model weights, compute capabilities and training history as reusable research assets so community inference and model development can grow on the same provenance layer.

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

Long-term blockers between the current local foundation and a world-scale DSCC are tracked in the [世界規模化に向けた未解決課題レジストリ](docs/GLOBAL_SCALE_CHALLENGES.ja.md). It is a living backlog for future agents and contributors: an item remains unresolved until its implementation, threat assumptions, measurements and remaining limits are recorded.

## Design proposals

[計算で整理する共有記憶 — Computational Memory](docs/proposals/COMPUTATIONAL_MEMORY.ja.md) proposes preserving original research records while using versioned embeddings, lexical search and provenance-aware graph retrieval to organize memory across different AI models. It includes primary-source references, compatibility requirements and an implementation handoff related to T007. **Proposal only; no memory-search implementation or benchmark result is introduced by this document.**

[分野を越える探索地図 — Exploration Atlas](docs/proposals/EXPLORATION_ATLAS.ja.md) extends that direction to trial-and-error paths across engineering, model development and everyday experience. It specifies typed episodes, independent semantic/structural retrieval, explicit analogy mappings, trial-backed transfer reports and source-linked motifs. [Implementation contracts](docs/proposals/exploration-atlas/IMPLEMENTATION.md) and [T010](docs/tasks/T010.md) include draft schemas, synthetic examples and executable contract tests. **The atlas application, semantic extraction, retrieval quality and map UI are not yet implemented or demonstrated.**

[みんなで使い、みんなで育てるオープンLLM計算コモンズ — Distributed Open Model Commons](docs/proposals/DISTRIBUTED_OPEN_MODEL_COMMONS.ja.md) defines a long-term DSCC goal: public inference for open models, voluntary compute contribution, globally distributed low-communication training, and provenance-preserving community model research. It separates results already demonstrated by prior decentralized-training research from the additional heterogeneous, adversarial and public-network problems DSCC would still need to solve. **Proposal only; DSCC currently has no distributed inference, GPU worker or model-training implementation.**

## Attribution and licensing

Original DSCC concept: Yusuke Maeda. This initial code and new implementation documents are provided under the MIT license in `LICENSE`. Material in `docs/reference/` is retained from the supplied DSCC research packet with separate attribution and provenance; third-party software and future research assets retain their own licenses. The concept-paper DOI identifies the paper, not a software-release DOI.
