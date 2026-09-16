# DSCC Desktop validation record

This report distinguishes the tested local source from the GitHub publication and from the unimplemented product. Software version: **0.0.1**. Original source commit: `592e9f9d0b3779ddd7e5f50a2b3a749504b7cc45` (retained in `SOURCE_COMMIT.txt`).

## Publication-time local rerun

The source Git bundle supplied for this project was cloned into a clean working directory. The following finite test run completed before upload:

```text
PYTHONPATH=src python -m pytest -q --junitxml=/mnt/data/dscc_publish/test-rerun.xml
....................................................................     [100%]
68 passed in 28.59s
```

The path above records the actual build-environment command; it is not a required installation path. To repeat the suite locally, use the README commands and choose any output path. The rerun used Python 3.13.5 on Linux. The suite includes the CLI demo and actual stdio subprocess exchanges.

## Coverage and its limits

The 68 tests cover canonical metadata, CID vectors, Unicode ordering, malformed and oversized data, signature tampering, missing parents, explicit trusted signing keys, unrelated bundle payloads, atomic rollback, logical quota failure, persistence, concurrent threads and four writer processes, audit-chain checks, approval/state integrity/cancellation/recovery, bounded tool admission, MCP negotiation/errors, eight tools, resource pagination, configuration generation, and cross-session reuse.

The MCP clients in the tests are synthetic clients, **not** installed LM Studio or Codex applications. The three demo nodes are separate directories on one machine and transfer explicit files. They do not test internet networking, NAT traversal, malicious independent operators, GPU sharing or arbitrary-code isolation. The built-in integer function is trusted application code, not a sandbox.

## Source-package evidence retained from the earlier build

The earlier starter-package validation recorded the same 68 passing tests, a successful local demo, schema/structure checks, a built wheel, and an offline wheel installation and demo in a separate virtual environment. Those are earlier build records, not new remote CI results. The original source package checked 11 reference files; this software publication retains nine source files and links the full manuscript and raster figure through the paper DOI. See `docs/reference/AVAILABILITY.md` and `SHA256SUMS.txt`.

## GitHub-specific verification

The application source and task pack are published in `AwakeningOS/DSCC`. Repository links and contributor instructions have been adapted to that name. The original software package is still named `dscc-desktop`.

The committed Actions workflow is configured for Linux and Windows with Python 3.11 and 3.13. **A workflow file is not evidence of a successful run.** Consult the Actions page and the commit-specific results for actual outcomes. Required status checks and branch protection must be enabled separately by the owner.

No GUI, actual host-app session, public P2P deployment, GPU worker, arbitrary-code sandbox, payments, model training, or autonomous background research loop has been demonstrated. This is not a production-readiness, security-proof or performance claim.

## Reproduction

```sh
python -m venv .venv
# Activate the virtual environment for your operating system.
python -m pip install -e '.[dev]'
python -m pytest -q
python -m dscc demo
python scripts/check_repository.py
```

Record each subsequent agent's actual commands, environment, outputs and untested cases in its PR and handoff. Never extend these results by inference.
