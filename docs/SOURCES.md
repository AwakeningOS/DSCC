# Sources and verification boundary

The original starter's source review was recorded on 2026-09-17. Sources establish component capabilities; they do not validate DSCC's integrated product. The GitHub publication step does not claim a new full literature audit.

* **Project source:** Yusuke Maeda, *Distributed Scientific Cognition Commons*, DOI https://doi.org/10.5281/zenodo.22782576. The supplied implementation brief, roadmap, threat model, metadata, bibliography and conceptual schemas are retained in `docs/reference/` with SHA-256 values. The full manuscript and figures are referenced through the DOI rather than duplicated in this software repository. They are concept material, not executed software.
* **MCP stdio, lifecycle and tools:** https://modelcontextprotocol.io/specification/2025-11-25/basic/transports ; https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle ; https://modelcontextprotocol.io/specification/2025-11-25/server/tools . These establish newline JSON-RPC, capability/version negotiation and tools.
* **Official Python MCP SDK:** https://py.sdk.modelcontextprotocol.io/ and https://py.sdk.modelcontextprotocol.io/v1/ . The documentation distinguishes current and maintenance release lines. The SDK was not installed in the initial build environment; see ADR-0003.
* **LM Studio MCP host:** https://lmstudio.ai/docs/app/mcp and https://lmstudio.ai/blog/lmstudio-v0.3.17 . Local stdio MCP configuration through `mcp.json` is documented. No LM Studio GUI session was tested here.
* **Codex MCP configuration:** https://developers.openai.com/codex/mcp/ . Local client configuration supports command/args for stdio. Product naming/UI may differ by installed version. No Codex desktop session was tested here.
* **AGENTS.md:** https://developers.openai.com/codex/guides/agents-md/ . Supports repository-local instructions; a file is not an autonomous scheduler.
* **Content addressing:** https://docs.ipfs.tech/concepts/content-addressing/ . CID depends on codec, hash and encoding; identical bytes with different DAG/chunk settings can have different roots.
* **Kubo RPC:** https://docs.ipfs.tech/reference/kubo/rpc/ . Administrative RPC is not a public peer API and must not be exposed to untrusted network clients.
* **JSON canonicalization:** https://www.rfc-editor.org/rfc/rfc8785 . M0 uses only its documented safe-integer/string subset.
* **GitHub repository creation:** https://cli.github.com/manual/gh_repo_create . Used for the prepared owner-run publishing helper.

Original bibliography is retained separately. Its citations have not all been re-audited for this software starter; do not copy its feasibility claims into a release announcement as measured results.
