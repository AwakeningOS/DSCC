# DSCC Desktop

**Local AI. Shared scientific experience. Participant-owned compute.**

DSCC Desktop is the application project for **Distributed Scientific Cognition Commons**, proposed by **Yusuke Maeda**. The target product lets a person connect a local AI application, select research assets to share, and contribute explicitly authorized storage or computation. Models and computers may change while research artifacts remain reusable.

[Concept paper — DOI: 10.5281/zenodo.22782576](https://doi.org/10.5281/zenodo.22782576) · [日本語ガイド](docs/START_HERE.ja.md) · [Architecture](docs/ARCHITECTURE.ja.md) · [Development status](docs/STATUS.md) · [Agent instructions](AGENTS.md) · [Development issues](https://github.com/AwakeningOS/DSCC/issues)

## What this repository contains

This is **a tested local foundation, not a released P2P/GPU-sharing desktop app**. It contains the full target architecture, interface boundaries, source-paper traceability, collaboration tasks, and a runnable first slice:

* Persistent, content-addressed research records with Ed25519 signatures and parent links.
* A transactional SQLite catalog, keyword search, bounded records, and signed local events.
* Explicit bundle export/import with signature, identity and dependency checks.
* Owner-approved local computation using one built-in deterministic integer-analysis tool.
* A small MCP stdio server: search, read, record, verify, inspect tools, submit a pending job, and inspect job status. Models cannot approve/run jobs through this adapter.

**Not implemented:** internet P2P, NAT traversal, remote jobs, GPU execution, arbitrary-code sandboxes, payments, native desktop UI, installers, or unattended model-development loops. Host applications (LM Studio/Codex) have not been launched here. See `reports/validation.md` for the exact tests actually run.

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

## Connect an AI application

```sh
python scripts/make_client_config.py --home ~/.dscc --out ./client-config
```

This generates `lmstudio.mcp.json` and `codex.config.toml` with the **actual Python executable** and an absolute data-directory path. Merge the generated entries into your application's configuration; do not overwrite existing settings. The generator does not change another application's files. [Detailed connection guide](docs/INTEGRATIONS.ja.md).

## Continue collaboratively

Give a coding agent `AGENTS.md`, then choose one ready task from `docs/TASKS.md` and its matching [GitHub Issue](https://github.com/AwakeningOS/DSCC/issues). Each task includes dependencies, edit boundaries and acceptance tests. Work on one branch per task, use separate worktrees for concurrent agents, and open a pull request with recorded validation. The task pack prepares collaboration; it does not launch or schedule agents by itself.

The repository is **AwakeningOS/DSCC**. The application/package name remains `dscc-desktop`. See [GitHub collaboration setup](docs/GITHUB_SETUP.ja.md) for instructions. Repository rules and required reviews must be enabled separately by the owner; committing a workflow file does not configure branch protection.

## Design proposals

[計算で整理する共有記憶 — Computational Memory](docs/proposals/COMPUTATIONAL_MEMORY.ja.md) proposes preserving original research records while using versioned embeddings, lexical search and provenance-aware graph retrieval to organize memory across different AI models. It includes primary-source references, compatibility requirements and an implementation handoff related to T007. **Proposal only; no memory-search implementation or benchmark result is introduced by this document.**

## Attribution and licensing

Original DSCC concept: Yusuke Maeda. This initial code and new implementation documents are provided under the MIT license in `LICENSE`. Material in `docs/reference/` is retained from the supplied DSCC research packet with separate attribution and provenance; third-party software and future research assets retain their own licenses. The concept-paper DOI identifies the paper, not a software-release DOI.
