# ADR-0001 — Keep the core independent of UI, models and networking

Status: adopted for M0. Original basis: DSCC paper §§3–5 and the supplied implementation brief.

The full system has separate storage, mutable state, execution, verification and model adapters. M0 implements persistent local contracts and explicit bundle exchange. It does not simulate a successful P2P or GPU service. This lets one owner test the experience lifecycle without recruiting peers. A later peer adapter exchanges the same versioned records.

Python is the initial core language. SQLite transactions coordinate independent local MCP processes. A service boundary and keychain follow in M1. The adapter must not make a model's natural-language request equivalent to an OS execution permission.
