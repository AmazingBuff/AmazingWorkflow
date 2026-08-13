---
description: Start or continue the gated small-project delivery workflow
argument-hint: "<request or continuation context>"
---

Act as the main-session orchestrator for the small-project workflow. Treat the
following text as the user's request or continuation context:

$@

Read `.pi/skills/small-project-workflow/references/SPEC.md` and the installed
`small-project-*` skills before choosing a phase. Maintain the workflow state
and gates in the current session. Ask for solution confirmation and final user
acceptance when the specification requires them; neither may be inferred from
silence.

For isolated phase work, call `small_project_subagent` once per bounded packet
using only one of these roles: `decision`, `implementer`, `reviewer`,
`test-planner`, `test-runner`, or `reporter`. Keep writing work serial in one
worktree. Pass the complete packet and use each returned result as evidence;
the tool only reads project-local `.pi/agents` and never selects a fallback
model.
