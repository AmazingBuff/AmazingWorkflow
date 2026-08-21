# Lightweight Coding Agent Workflow v0.3

A two-phase coding workflow with a host-neutral Core and explicit host adapters:

1. The current user-facing task plans and freezes an implementation contract.
2. Exactly one implementation worker writes and verifies through one `VERIFIED` adapter.

The framework has no service, database, CLI, executable runtime, or dependency. It preserves explicit implementation-model choice and one-writer ownership, and adds bounded version-control planning and evidence to the `DONE/BLOCKED/FAILED` result schemas.

## Architecture

```text
Planner Skill ──loads──> Core Protocol
      │                    │
      ├──validates──> Host Adapter Contract
      │                    │
      └──selects exactly one VERIFIED Adapter
                               │
                               └──dispatches one implementation worker
```

Core owns contract, state, worktree, single-writer, version-control authority, and result rules. The Adapter Contract defines nine required capabilities. A host adapter maps those capabilities to one host without leaking host paths, worker names, model precedence, or lifecycle terminology into Core.

The Planner completes the adapter gate before requesting implementation approval or allowing product-code writes. Missing, ambiguous, incompatible, or incomplete adapters produce `CAPABILITY_UNAVAILABLE`; the Planner does not implement as a fallback.

## Support states

| State | Meaning | Implementation writes |
| --- | --- | --- |
| `VERIFIED` | All required operations are mapped and exercised for claimed surfaces. | Allowed after approval and revalidation. |
| `EXPERIMENTAL` | Runnable mapping with incomplete verification. | Disabled by default in v0.3. |
| `AUTHORING_ONLY` | Template or design material; no executable support claim. | Never. |
| `UNSUPPORTED` | One or more required operations have no mapping. | Never. |

## Support matrix

| Host / artifact | State | Adapter | Surfaces |
| --- | --- | --- | --- |
| Codex | `VERIFIED` | `codex` `0.3` | Desktop, CLI, IDE extension |
| Generic adapter template | `AUTHORING_ONLY` | none | authoring reference only |
| Claude Code, Cursor, OpenCode, Gemini CLI | `UNSUPPORTED` | none | none |
| Any unnamed host | `UNSUPPORTED` | none | none |

Codex is the sole verified host. The generic template does not claim support for any host.

## Source package

```text
lightweight-coding-agent-workflow-spec/
├── CHANGELOG.md
├── DESIGN.md
├── README.md
├── agents/
│   └── lightweight_implementer.toml
└── skills/
    └── lightweight-coding-workflow/
        ├── SKILL.md
        ├── agents/openai.yaml
        ├── assets/implementation-contract.md
        └── references/
            ├── protocol.md
            ├── adapter-contract.md
            ├── git-commit-convention.md
            └── adapters/
                ├── codex.md
                └── template.md
```

Key references:

- [Design and compatibility](DESIGN.md)
- [Planner Skill](skills/lightweight-coding-workflow/SKILL.md)
- [Core protocol](skills/lightweight-coding-workflow/references/protocol.md)
- [Host Adapter Contract](skills/lightweight-coding-workflow/references/adapter-contract.md)
- [Canonical Git commit and Changelog convention](skills/lightweight-coding-workflow/references/git-commit-convention.md)
- [Verified Codex Adapter](skills/lightweight-coding-workflow/references/adapters/codex.md)
- [Authoring-only Adapter Template](skills/lightweight-coding-workflow/references/adapters/template.md)

## Compatibility with v0.2

v0.3 preserves the v0.2 Codex execution model and installation behavior: the current main task remains Planner, one model-neutral `lightweight_implementer` performs writes, per-task model choice remains explicit, and permissions inherit from the parent task.

New v0.3 contracts retain the v0.2 fields and add a Version control section. Approved older contracts are never rewritten in place; resume them with matching protocol and adapter resources or create and approve a v0.3 revision.

The custom Agent TOML and UI metadata remain unchanged.

## Install for the current user

Install the same two components as v0.1:

- Copy `skills/lightweight-coding-workflow/` to the user-level Skill directory recognized by Codex. In the current local layout, this is `%USERPROFILE%\.codex\skills\lightweight-coding-workflow\`.
- Copy `agents/lightweight_implementer.toml` to `%USERPROFILE%\.codex\agents\lightweight_implementer.toml`.

Restart Codex if the Skill or custom Agent does not appear. The Agent intentionally omits `model`, `model_reasoning_effort`, and `sandbox_mode`; the verified Codex Adapter supplies per-task model mapping while permissions inherit from the parent task.

## Use

Invoke the Skill explicitly or describe a matching two-phase request:

```text
Use $lightweight-coding-workflow to plan this change with me.
After I approve the plan, use <implementation-model> for implementation.
```

On Codex, the verified Adapter keeps task records under `.codex/task-runs/<task-id>/`. The workflow does not modify `.gitignore` automatically.

For Git-backed work, the Planner reads the canonical convention and proposes the baseline, logical commit boundary, Changelog disposition and entry, Conventional Commit message, and separate commit and push authorities. Both authorities default to `none`; approving implementation never authorizes staging, committing, or pushing. Non-Git work records `version_control_system: none` and skips Git operations.

## Author another adapter

Start from the [authoring template](skills/lightweight-coding-workflow/references/adapters/template.md) and satisfy the [Host Adapter Contract](skills/lightweight-coding-workflow/references/adapter-contract.md). The template remains `AUTHORING_ONLY` until every required operation has concrete mapping and retained verification evidence. Filling placeholders alone does not promote support.

## Validate

Validate the Skill, parse the unchanged Agent TOML and UI YAML, resolve all relative Markdown references, check Core isolation and all nine adapter metadata/operation mappings, scan for unintended scaffold markers and trailing whitespace, and inspect repository scope before installation. Verify Codex Git handling in an isolated repository with read-only baseline inspection, exact-path staging, a compliant commit, a clean post-commit state, and no remote or push.

The authoritative behavior and acceptance scenarios are defined in [DESIGN.md](DESIGN.md).
