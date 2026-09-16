# Contributing

Read `AGENTS.md` for both human and agent contributions. Start with a READY task from `docs/TASKS.md`; reserve it in its GitHub issue once issues are created. Use a separate branch/worktree, keep a focused patch, and include tests and a handoff. Work can proceed serially with one person and several coding agents; concurrent paid agents are not a requirement.

Generated code must be reviewed just like human-written code. Citations and benchmark claims need primary sources or archived logs. Do not upload live research data, credentials or node signing keys. Use synthetic fixtures.

New contributed code uses MIT unless a directory explicitly carries another license. Imported libraries, tools, models and datasets retain their licenses. Preserve author and provenance information.

The default CI uses hosted GitHub runners only, no production node credentials and no contributor-owned GPU. Repository rule configuration (required reviews/checks) requires the owner to enable it on GitHub; supplying workflow YAML does not enable branch protection.
