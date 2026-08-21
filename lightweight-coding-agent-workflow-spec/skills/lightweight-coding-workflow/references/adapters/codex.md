---
host_adapter: "codex"
host_id: "codex"
display_name: "Codex Host Adapter"
protocol_version: "0.3"
adapter_version: "0.3"
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
verified_on: "2026-08-21"
---

# Codex Host Adapter

This adapter is the sole `VERIFIED` protocol 0.3 mapping. It implements the [Host Adapter Contract](../adapter-contract.md) for the [Core protocol](../protocol.md) while preserving the version 0.2 Codex workflow.

## Compatibility

| Item | Mapping |
| --- | --- |
| Core protocol | Exact version `0.3` |
| Adapter | `codex` version `0.3` |
| Planner | Current Codex main task and its selected model |
| Worker | Codex custom agent `lightweight_implementer` |
| Contract asset | Loaded Skill's `assets/implementation-contract.md` |
| Task records | Repository-local `.codex/task-runs/<task-id>/implementation-contract-v<revision>.md` |
| Result schemas | Core `DONE`, `BLOCKED`, and `FAILED` Markdown schemas |

## Operation map

| Capability | Operation | Codex mechanism | Failure mapping |
| --- | --- | --- | --- |
| Host identification | `identify_host` | Confirm the Skill is running in a Codex task and inspect the host-provided surface and tool capabilities without writing. | `CAPABILITY_UNAVAILABLE` before approval if identity is absent or ambiguous. |
| Planner binding | `bind_planner` | Keep the current main task as the sole Planner and user-facing task; resolve resources from the loaded Skill and task records from the repository root. | `CAPABILITY_UNAVAILABLE` if the task, repository, or loaded resources cannot be resolved. |
| Model validation | `validate_model` | Validate a user-approved Codex model override or explicit parent inheritance against host-provided choices and dispatch support. | Return to planning; never substitute a model or effort. |
| Worker dispatch | `dispatch_worker` | Spawn exactly one custom agent named `lightweight_implementer` with the Core dispatch envelope. | `CAPABILITY_UNAVAILABLE` before writes if custom agents or subagent dispatch are unavailable. |
| Permission inheritance | `inherit_permissions` | Let the worker inherit the main task's sandbox and approval policy; omit permission-broadening Agent fields. | `BLOCKED` if an in-scope action needs unavailable approval or authority. |
| Lifecycle control | `control_lifecycle` | Use Codex subagent ownership, continuation, interruption, stop, completion, and close controls; replace only after the writer is stopped or closed. | `BLOCKED` for unresolved ownership; `FAILED` for unrecoverable host control failure. |
| Progress reporting | `report_progress` | Observe the subagent task/thread and relay concise progress while raw logs remain with the worker. | `FAILED` only when progress/result state cannot be recovered after evidence-based attempts. |
| Result relay | `relay_result` | Receive the worker's final Markdown and validate its first line and required Core sections before Planner reporting. | Continue the same worker for an in-scope malformed result; otherwise `FAILED`. |
| Version-control management | `manage_version_control` | Use read-only Git commands for baselines; use exact-path staging and commit only under exact contract authority; push only under separate remote/refspec authority. | `BLOCKED` for authority, overlap, or baseline conflicts; `FAILED` for an unrecoverable authorized Git operation. |

## `identify_host`

Preconditions: the workflow Skill is loaded in a Codex task. Confirm host identity from host-provided task/tool metadata and confirm the active surface is one of `desktop`, `cli`, or `ide-extension`. Do not infer Codex solely from repository files or this adapter's presence.

Output: `host_id=codex`, the active surface, and availability evidence for custom-agent dispatch, permission inheritance, lifecycle observation, and result return.

## `bind_planner`

Bind the current main task, without spawning another planning agent. Its currently selected model remains the Planner model and only this task communicates with the user.

Resolve:

- the repository root from the current task workspace;
- the Core and adapter references from the loaded Skill location;
- the contract asset from the same loaded Skill;
- task records under `.codex/task-runs/<task-id>/` in the repository.

Creating a task record does not authorize product-code writes or an ignore-file change.

## `validate_model`

Use this Codex-specific precedence:

1. an exact model and optional reasoning effort explicitly approved for the current task;
2. a project default only after the user explicitly confirms it for the current task;
3. otherwise, remain in planning and ask the user to choose.

`inherit-parent (user-approved)` is valid only when the user explicitly approves inheritance. For that value, omit the Codex spawn model override deliberately. For a named model, pass the exact model override. Pass reasoning effort exactly when the selected model and dispatch interface support it.

If Codex does not expose or accept the selected model or effort, return to planning. Do not update the custom Agent TOML and do not fall back to another value.

## `dispatch_worker`

Preconditions:

- the contract is `APPROVED` and records `protocol_version: "0.3"`, `host_adapter: "codex"`, and `adapter_version: "0.3"`;
- no other write-capable subagent owns the worktree;
- model and permission validation passed;
- the installed custom Agent `lightweight_implementer` is available.

Spawn that custom Agent exactly once. Pass the absolute contract path, the absolute loaded Core-protocol path, task id, revision, and this instruction envelope:

```text
Execute approved contract <absolute-path>.
Read and follow result protocol <absolute-core-protocol-path>.
Task: <task-id>, revision <revision>.
Treat the contract as the sole authority.
Do not ask the user, expand scope, edit the contract, or spawn another agent.
Return exactly one STATUS: DONE, STATUS: BLOCKED, or STATUS: FAILED result using the referenced schema verbatim.
```

Apply the model mapping from `validate_model`; explicit parent inheritance intentionally supplies no model override.

## `inherit_permissions`

The worker inherits the main task's sandbox and approval policy. Keep `model`, `model_reasoning_effort`, and `sandbox_mode` absent from the model-neutral custom Agent file so per-task choices and host permissions remain authoritative.

Use Codex approval controls for in-scope operations that need elevation. A denied or unavailable permission that prevents acceptance is `BLOCKED`; the adapter never changes configuration to bypass it.

## `control_lifecycle`

Before spawn, confirm single-writer ownership. Continue the same subagent for bounded in-scope repair or an approved contract revision when possible. If the user changes material requirements, interrupt or stop the worker before planning resumes.

A replacement is permitted only after Codex confirms the earlier writer is stopped, completed, or closed. Ambiguous ownership is blocking because another spawn could violate the one-writer invariant.

## `report_progress`

Observe the implementation task/thread through Codex's subagent coordination controls. Keep command logs and intermediate implementation details in that task. Relay only concise progress or a decision-requiring block to the main task. Progress observation never authorizes another writer.

## `relay_result`

Receive one final worker result in the main task. Validate:

- the first line is exactly one Core status;
- all sections required by that status are present;
- changed paths, command exits, and acceptance evidence are explicit for `DONE`;
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

1. Revalidate `HEAD`, the index/staged state, worktree ownership, allowed paths, and required Changelog entry.
2. Stage only contract-authorized paths with `git add -- <exact-paths>` or, for an authorized mixed file, `git add -p -- <exact-path>`.
3. Inspect `git diff --cached --stat` and `git diff --cached`; reject unrelated content, missing required artifacts, secrets, temporary files, or a non-atomic boundary.
4. Validate the exact approved message against the canonical Conventional Commit rules, then execute one `git commit` with that message.
5. Record the resulting full SHA and message with `git rev-parse HEAD` and `git show --stat --oneline HEAD`, then inspect `git status --short` for the post-commit state.

Do not amend, squash, rebase, tag, rewrite history, or replace the current index as part of this operation. If commit authority exists but safe exact staging cannot preserve unrelated staged or working changes, return `BLOCKED` before mutation.

Push is a separate operation. Run `git push <approved-remote> <approved-source>:<approved-destination>` only when the contract grants exact push authority for that remote and refspec and the committed SHA matches the authorized logical change. Otherwise do not contact a remote and report `not-authorized` or `not-run` with the reason. Commit authority never implies push authority.

Return the Core version-control evidence fields without rewriting status: system, baseline, Changelog disposition, commit status or proposed message, and push status. A denied authority, ownership conflict, or contract mismatch is `BLOCKED`; an evidence-backed failure of an authorized operation that cannot progress under the same environment is `FAILED`.

## Verification basis

This `VERIFIED` mapping preserves the existing Codex behavior: main-task planning, explicit per-task implementation-model choice, the model-neutral `lightweight_implementer`, inherited permissions, one subagent writer, structured result relay, and unchanged user-level Skill plus Agent installation layout. Protocol 0.3 validation checks adapter metadata and all nine operation mappings before approval and dispatch. On 2026-08-21, version-control management was exercised in an isolated Git repository for read-only baseline inspection, exact-path staging, a compliant bounded commit, clean post-commit state, and no remote or push.
