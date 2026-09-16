# ADR-0003 — Minimal stdio MCP adapter with explicit compatibility scope

Status: temporary implementation, replaceable via T002.

The build environment could not resolve the package index to install the MCP SDK. Rather than claim an unexecuted integration, M0 contains a small tested JSON-RPC stdio subset: initialize, initialized notification, ping, tools/list, tools/call, resources/list and resources/read. It advertises only supported features for protocol 2025-11-25 and 2025-06-18.

No HTTP transport, OAuth, subscriptions, progress, sampling, prompts or MCP task extension is claimed. DSCC's own pending jobs are not MCP protocol tasks. Replace this adapter with the official Python SDK after dependency availability and host compatibility are verified. Preserve tool contracts and run the same subprocess tests against both adapters.
