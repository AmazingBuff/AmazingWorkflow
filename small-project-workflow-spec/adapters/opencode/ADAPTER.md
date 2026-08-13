# OpenCode adapter source

This directory is source material for rendering the small-project workflow into
OpenCode. It intentionally contains no model defaults. Use the suite-level
`scripts/build_harness.py` builder; do not copy unrendered templates.

The builder replaces the four required tokens in [`harness.json`](harness.json),
places the agents in `.opencode/agents/`, and copies the command to
`.opencode/commands/`. The command selects
the primary `small-project-orchestrator` agent and passes OpenCode's
`$ARGUMENTS` placeholder to it.

Install the workflow package as a unit under `.opencode/skills/`, preserving
each existing skill directory and placing the authoritative workflow spec at
`.opencode/skills/small-project-workflow/references/SPEC.md`. The workflow
skill reads that in-package reference first; a root-level copy is not the
installed authority.

Before building, use `opencode models` to verify the exact provider/model IDs
and variants. The builder records caller-provided values but cannot prove the
target OpenCode process is authenticated; live discovery remains unverified
until the generated project is opened in OpenCode.

The templates use OpenCode agent frontmatter for `description`, `mode`,
`model`, `variant`, `steps`, and `permission`. The orchestrator alone may call
the listed `small-project-*` phase agents. Every phase agent denies Task and can
load only `small-project-*` skills. The reviewer is read-only; the test runner
denies edits and asks before shell execution.

See OpenCode's [agent documentation](https://opencode.ai/docs/agents/),
[permission documentation](https://opencode.ai/docs/permissions/), and
[command documentation](https://opencode.ai/docs/commands/) for the runtime
semantics used by these templates.
