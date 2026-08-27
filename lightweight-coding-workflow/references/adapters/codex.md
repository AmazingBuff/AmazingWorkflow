---
host_adapter: "codex"
host_id: "codex"
display_name: "Codex Host Adapter"
protocol_version: "0.6"
adapter_version: "0.6"
support_state: "VERIFIED"
supported_surfaces:
  - "desktop"
  - "cli"
  - "ide-extension"
capabilities:
  - "host_identification"
  - "planner_binding"
  - "model_validation"
  - "worker_dispatch"
  - "permission_inheritance"
  - "lifecycle_control"
  - "progress_reporting"
  - "result_relay"
  - "version_control_management"
optional_capabilities:
  - "read_only_scout_dispatch"
verified_on: "2026-08-25"
---

# Codex Host Adapter

Implementation dispatch eligibility: **yes**, only after contract/model approval and immediate capability revalidation. Scout dispatch eligibility: **yes**, for read-only Phase 1 discovery per the [Context Routing reference](../context-routing.md).

This adapter is the sole `VERIFIED` protocol `0.6` mapping. It implements the [Host Adapter Contract](../adapter-contract.md) for the [Core protocol](../protocol.md), carries feature-documentation evidence without adding a capability, and preserves the model-neutral custom Agent.

## Compatibility

| Item | Mapping |
| --- | --- |
| Core protocol | Exact version `0.6` |
| Adapter | `codex` version `0.6` |
| Planner | Current Codex main task and its selected model |
| Worker | Codex custom agent `lightweight_implementer` |
| Worker source | [lightweight_implementer.toml](../../agents/lightweight_implementer.toml) |
| Scout | Codex custom agent `lightweight_scout` with a validated cheap model, per the [Context Routing reference](../context-routing.md) |
| Scout source | [lightweight_scout.toml](../../agents/lightweight_scout.toml) |
| Contract asset | Loaded Skill's `assets/implementation-contract.md` |
| Feature documentation | Loaded convention and template plus contract-selected repository paths |
| Coding-rule components | Loaded Skill's `assets/coding-rules/**`, listed by absolute path in the contract |
| Task records | Repository-local `.codex/task-runs/<task-id>/implementation-contract-v<revision>.md` |
| Result schemas | Core `DONE`, `BLOCKED`, and `FAILED` Markdown schemas with `DOCUMENTATION` evidence; scouts return evidence packets per the Context Routing reference |

Protocol `0.6` requires exact adapter metadata. Older approved contracts remain immutable and continue only with matching historical resources or a newly approved revision.

## Operation map

| Capability | Operation | Codex mechanism | Failure mapping |
| --- | --- | --- | --- |
| Host identification | `identify_host` | Confirm the Skill is running in a Codex task and inspect host-provided surface and tool capabilities without writing. | `CAPABILITY_UNAVAILABLE` before approval if identity is absent or ambiguous. |
| Planner binding | `bind_planner` | Keep the current main task as the sole Planner; resolve resources from the loaded Skill and task records from the repository root. | `CAPABILITY_UNAVAILABLE` if the task, repository, or loaded resources cannot be resolved. |
| Model validation | `validate_model` | Validate a user-approved Codex model override or explicit parent inheritance against the host's current resolution order and dispatch support. | Return to planning; never substitute a model or effort. |
| Worker dispatch | `dispatch_worker` | Spawn exactly one custom agent named `lightweight_implementer` with the complete Core dispatch envelope. | `CAPABILITY_UNAVAILABLE` before writes if custom agents or subagent dispatch are unavailable. |
| Permission inheritance | `inherit_permissions` | Let the worker inherit the main task's live sandbox and approval policy; omit permission-broadening Agent fields. | `BLOCKED` if an in-scope action needs unavailable approval or authority. |
| Lifecycle control | `control_lifecycle` | Use Codex subagent ownership, continuation, interruption, stop, completion, and close controls; replace only after the writer is stopped or closed. | `BLOCKED` for unresolved ownership; `FAILED` for unrecoverable host control failure. |
| Progress reporting | `report_progress` | Observe the subagent task and relay concise progress while raw logs remain with the worker. | `FAILED` only when progress/result state cannot be recovered after evidence-based attempts. |
| Result relay | `relay_result` | Receive the worker's final Markdown and validate its status plus every required Core section, including `DOCUMENTATION`. | Continue the same worker for an in-scope malformed result; otherwise `FAILED`. |
| Version-control management | `manage_version_control` | Use read-only Git commands for baselines; use exact-path staging and commit only under exact contract authority; push only under separate remote/refspec authority. | `BLOCKED` for authority, overlap, or baseline conflicts; `FAILED` for an unrecoverable authorized Git operation. |
| Read-only scout dispatch (optional) | `dispatch_scout` | Spawn the `lightweight_scout` custom agent with a validated cheap model, the scout task packet, and exactly its assigned source selectors; relay evidence packets; no write path. | `CAPABILITY_UNAVAILABLE` before scouting if custom agents or model overrides are unavailable; the task falls back to the fast lane with the restriction recorded. |

## `identify_host`

Preconditions: the workflow Skill is loaded in a Codex task. Confirm host identity from host-provided task/tool metadata and confirm the active surface is one of `desktop`, `cli`, or `ide-extension`. Do not infer Codex solely from repository files or this adapter's presence.

Output: `host_id=codex`, the active surface, and availability evidence for custom-agent dispatch, permission inheritance, lifecycle observation, result return, and version-control management.

## `bind_planner`

Bind the current main task without spawning another planning agent. Its currently selected model remains the Planner model, and only this task communicates with the user.

Resolve:

- the repository root from the current task workspace;
- the Core, Adapter Contract, Git convention, feature-documentation convention, feature template, and coding-rule components from the loaded Skill location;
- the implementation-contract asset from the same loaded Skill;
- task records under `.codex/task-runs/<task-id>/` in the repository.

Creating a task record does not authorize product-code writes or an ignore-file change.

## `validate_model`

Codex currently resolves a spawned custom Agent's model and reasoning fields from an explicit spawn value, then `[agents]` defaults, then the parent value; fields present in the custom Agent file take precedence when that file is applied. The package's custom Agent intentionally omits `model`, `model_reasoning_effort`, and `sandbox_mode`.

Use this validation order:

1. For an exact model and optional reasoning effort explicitly approved for the task, confirm that Codex exposes and accepts both values, then pass them as exact spawn overrides.
2. For `inherit-parent (user-approved)`, omit spawn model and effort overrides only after confirming that active `[agents]` defaults will not replace the parent's values. If a default would intervene, return to planning to approve the effective default or choose an exact override.
3. A project default is valid only after the user explicitly approves its exact effective value for the current task.

If Codex cannot expose or accept the selected model or effort, return to planning. Do not update the custom Agent TOML and do not fall back to another value. This behavior follows the current [official Codex custom-agent model resolution](https://developers.openai.com/codex/subagents).

## `dispatch_worker`

Preconditions:

- the contract is `APPROVED` and records `protocol_version: "0.6"`, `host_adapter: "codex"`, and `adapter_version: "0.6"`;
- no other write-capable subagent owns the worktree;
- model and permission validation passed;
- every applicable coding-rule path and Documentation obligation resolves;
- the installed custom Agent `lightweight_implementer` is available.

Spawn that custom Agent exactly once. Pass the absolute contract path, the absolute loaded Core-protocol path, task id, revision, approved model selection, and absolute coding-rule component paths in this instruction envelope:

```text
Execute approved contract <absolute-path>.
Read and follow result protocol <absolute-core-protocol-path>.
Task: <task-id>, revision <revision>.
Model selection: <adapter-validated-selection>.
Before editing, read every Applicable coding rules path from the contract.
Treat the contract as the sole authority.
Do not ask the user, expand scope, edit the contract, or spawn another agent.
Return exactly one STATUS: DONE, STATUS: BLOCKED, or STATUS: FAILED result using the referenced schema, including DOCUMENTATION evidence.
```

Apply the model mapping from `validate_model`; verified explicit parent inheritance intentionally supplies no spawn override only after the default-interception check passes.

## `inherit_permissions`

The worker inherits the main task's live sandbox and approval policy. Keep `model`, `model_reasoning_effort`, and `sandbox_mode` absent from the model-neutral custom Agent file so per-task choices and host permissions remain authoritative.

Use Codex approval controls for in-scope operations that need elevation. A denied or unavailable permission that prevents acceptance is `BLOCKED`; the adapter never changes configuration to bypass it.

## `control_lifecycle`

Before spawn, confirm single-writer ownership. Continue the same subagent for bounded in-scope repair or an approved contract revision when possible. If the user changes material requirements, interrupt or stop the worker before planning resumes.

A replacement is permitted only after Codex confirms the earlier writer is stopped, completed, or closed. Ambiguous ownership is blocking because another spawn could violate the one-writer invariant.

## `report_progress`

Observe the implementation task through Codex's subagent coordination controls. Keep command logs and intermediate implementation details in that task. Relay only concise progress or a decision-requiring block to the main task. Progress observation never authorizes another writer.

## `relay_result`

Receive one final worker result in the main task. Validate:

- the first line is exactly one Core status;
- all sections required by that status are present;
- changed paths, command exits, and acceptance evidence are explicit for `DONE`;
- `DOCUMENTATION` reports the decision, canonical document and index, navigation, validation, and freshness evidence;
- missing evidence is not described as success.

The Planner may perform read-only confirmation. In-scope repair returns to the same worker; the Planner does not edit product code.

## `manage_version_control`

Inputs are the approved contract's Version control section: system, baseline, logical commit boundary, Changelog disposition and proposed entry, proposed Conventional Commit message, commit authority, push authority, and any exact push target.

For `version_control_system: none`, run no Git command and return not-applicable evidence. For Git, establish or revalidate the baseline with read-only commands scoped to the resolved repository:

```text
git rev-parse --show-toplevel
git branch --show-current
git rev-parse HEAD
git status --short --untracked-files=all
git diff --cached --name-status
```

Record branch or detached state, revision, staged paths, and uncommitted paths. Do not use a nominally diagnostic command that writes the index, `HEAD`, refs, configuration, or object database. A baseline change or staged path outside the approved logical boundary is `BLOCKED` when safe continuation would require touching user work or revising the contract.

When commit authority is `none`, do not run `git add`, `git commit`, or `git push`; report the approved proposed message. When the contract grants exact commit authority:

1. Revalidate `HEAD`, the index/staged state, worktree ownership, allowed paths, required feature documentation, and required Changelog entry.
2. Stage only contract-authorized paths with `git add -- <exact-paths>` or, for an authorized mixed file, `git add -p -- <exact-path>`.
3. Inspect `git diff --cached --stat` and `git diff --cached`; reject unrelated content, missing required artifacts, secrets, temporary files, or a non-atomic boundary.
4. Validate the exact approved message against the canonical Conventional Commit rules, then execute one `git commit` with that message.
5. Record the resulting full SHA and message, then inspect `git status --short` for the post-commit state.

Do not amend, squash, rebase, tag, rewrite history, or replace the current index as part of this operation. If safe exact staging cannot preserve unrelated staged or working changes, return `BLOCKED` before mutation.

Push is separate. Run `git push <approved-remote> <approved-source>:<approved-destination>` only when the contract grants exact push authority for that remote and refspec and the committed SHA matches the authorized logical change. Otherwise do not contact a remote. Commit authority never implies push authority.

Return the Core version-control evidence fields without rewriting status. A denied authority, ownership conflict, or contract mismatch is `BLOCKED`; an evidence-backed failure of an authorized operation that cannot progress under the same environment is `FAILED`.

## `dispatch_scout` (optional capability)

Preconditions:

- the routing decision chose the orchestrated lane and was presented to the user with the scout model;
- the scout model passed `validate_model` with the same validation order as the implementation model;
- a validated orchestration plan and scout task packets exist under the task-record directory;
- the `lightweight_scout` custom agent is available.

Spawn `lightweight_scout` once per task packet with an explicit model override for the validated cheap model. Pass the task packet, the exact assigned source selectors, and the evidence-packet response contract from the Context Routing reference. Scouts never receive the parent transcript, never self-expand beyond `request`-mode expansion requests, and never receive a write path; permission inheritance keeps them inside the main task's read-only discipline.

Relay evidence packets back to the Planner, which merges them per the Context Routing reference. A scout failure is a routing fallback: switch the affected discovery to the fast lane and record the restriction in the proposal, or return to the routing decision. Scout dispatch never satisfies or substitutes any part of `dispatch_worker`.

## Verification basis

This `VERIFIED` mapping preserves main-task planning, explicit per-task implementation-model choice, the model-neutral `lightweight_implementer`, inherited permissions, one subagent writer, documentation-aware result relay, and the user-level Skill plus Agent installation layout. Protocol `0.6` validation checks adapter metadata, all nine operation mappings, the optional scout-dispatch mapping, the write gate, bundled-rule integrity, feature-documentation integration, and source/install parity. The 2026-08-25 release revalidated current inherited-model resolution and retained the prior isolated Git and lifecycle evidence for unchanged operations.
