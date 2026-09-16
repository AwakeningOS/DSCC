# Development tasks

Choose one READY task per branch. Check the matching GitHub Issue and coordinate a claim before editing. Do not start a BLOCKED task by inventing the missing backend. The task IDs remain stable even if GitHub issue numbers differ.

| ID | Task | Status | Dependencies |
|---|---|---|---|
| [T001](tasks/T001.md) | Local service and owner permissions | READY | — |
| [T002](tasks/T002.md) | Official MCP SDK and host-app integration | READY | — |
| [T003](tasks/T003.md) | WASI executor with enforceable limits | READY | — |
| [T004](tasks/T004.md) | Desktop user interface | BLOCKED | T001 |
| [T005](tasks/T005.md) | Explicit peer invitations and artifact transport | READY | — |
| [T006](tasks/T006.md) | GPU worker capability and isolation matrix | BLOCKED | T001, T003 |
| [T007](tasks/T007.md) | Research object adapters and catalog rebuild | READY | — |
| [T008](tasks/T008.md) | Reproducible shared-world example | BLOCKED | T003, T007 |
| [T009](tasks/T009.md) | Adversarial verification and release audit | READY | — |

T001, T002, T003, T005, T007 and T009 can start from M0. Shared schema/core edits require coordination. Start the security reviewer on a different worktree from the implementer.

Issues: https://github.com/AwakeningOS/DSCC/issues
