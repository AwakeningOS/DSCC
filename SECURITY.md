# Security status

This is a local research prototype. Do not expose it as a public execution service. The MCP server uses stdio, opens no listening port, and offers no arbitrary-code execution or publication tool. Its process runs with the launching OS user's permissions, so installation itself requires trust in this repository.

The core checks bounded inputs, CID integrity, Ed25519 signatures, parent availability, explicit signer trust on import, storage-accounting limits and legal job-state transitions. The local audit chain detects changes to retained events; it cannot detect tail deletion without an externally anchored head and does not protect against a malicious owner who controls the signing key.

Private keys are unencrypted files in an owner-only node directory in M0. Unix permissions are set where supported; Windows ACLs and OS keychain integration require a later task. A model given a separate unrestricted terminal can access what its OS user can access. The MCP surface's restrictions do not secure an unrestricted terminal.

Only the built-in integer summary runs. It is trusted application code, **not** a sandbox for third-party Python. Resource limits are input bounds and logical storage accounting, not an OS CPU/GPU isolation boundary. Imported bundle content is data and never executed. Nested private dependencies can be disclosed by a deliberate export; inspect them before sharing.

Report a vulnerability privately to the repository owner through a configured security advisory channel. Do not publish exploit details in a public issue before a private route is agreed. No private vulnerability-reporting endpoint has been provisioned by this starter.
