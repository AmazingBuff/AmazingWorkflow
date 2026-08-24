---
host_adapter: "dsh"
host_id: "dsh"
display_name: "DeepSeek Harness Host Adapter"
protocol_version: "0.4"
adapter_version: "0.4"
support_state: "EXPERIMENTAL"
supported_surfaces:
  - "web-gui"
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
verified_on: null
---

# DeepSeek Harness Host Adapter

This adapter maps the [Host Adapter Contract](../adapter-contract.md) onto the DeepSeek Harness (DSH) so the [Core protocol](../protocol.md) can dispatch one implementation worker from a DSH session. It is authored against protocol `0.4`.

`support_state` is `EXPERIMENTAL`: every required operation has a concrete mapping below, but the operations have not yet been exercised end to end with retained evidence. Under protocol `0.4` this adapter is selectable only when the user explicitly approves it by name — acknowledging its state — in the same approval that grants the implementation contract, and the contract records `host_adapter: dsh`, `adapter_version`, and the acknowledged `EXPERIMENTAL` state. Promotion to `VERIFIED` requires the [verification checklist](#verification-checklist) to be executed with retained evidence and a deliberate metadata update; it is never claimed from this document alone.

## Compatibility

| Item | Mapping |
| --- | --- |
| Core protocol | `0.4` (additive over `0.3`) |
| Adapter | `dsh` version `0.4` |
| Planner | The current DSH main task and its deployed model |
| Worker | One isolated DSH background subagent |
| Contract asset | Loaded Skill's `assets/implementation-contract.md` |
| Coding-rule components | Loaded Skill's `assets/coding-rules/**`, listed by absolute path in the contract |
| Task records | Repository-local `.dsh/task-runs/<task-id>/implementation-contract-v<revision>.md` |
| Result schemas | Core `DONE`, `BLOCKED`, and `FAILED` Markdown schemas |

## Operation map

| Capability | Operation | DSH mechanism | Failure mapping |
| --- | --- | --- | --- |
| Host identification | `identify_host` | Confirm the task runs in a DSH session from host-provided signals: the harness-native tool surface (native `pwsh`/file tools and the skill loader), the DSH skill catalog, and `DSH_*` session environment variables read via `$env:DSH_*`. Never infer DSH from repository files or this file's presence. | `CAPABILITY_UNAVAILABLE` before approval if identity is absent or ambiguous. |
| Planner binding | `bind_planner` | Keep the current main task as the sole Planner; resolve the Core and adapter references from the loaded skill's base directory, the contract asset from the same skill, the repository root from the workspace working directory, and task records under `.dsh/task-runs/<task-id>/`. | `CAPABILITY_UNAVAILABLE` if the task, repository, or loaded resources cannot be resolved. |
| Model validation | `validate_model` | Validate the user-approved selection against what this surface can represent: `inherit-parent (user-approved)` is the primary supported value (the worker inherits the Planner's deployed model); a session reasoning-mode change is honored only when explicitly approved and recorded in the contract. | `BLOCKED` when the user requires a distinct exact model or reasoning effort this surface cannot represent for a subagent; return to planning with the options (accept the parent model, or replan on a host that supports exact override). Never substitute silently. |
| Worker dispatch | `dispatch_worker` | Spawn exactly one isolated subagent through the native `subagent` tool with a complete standalone prompt carrying the Core dispatch envelope: absolute contract path, absolute Core protocol path, task id, revision, model selection, absolute coding-rule component paths, and the instructions to treat the contract as sole authority, ask no user questions, spawn no other writer, and return exactly one result schema. | `CAPABILITY_UNAVAILABLE` before writes if subagent dispatch is unavailable. |
| Permission inheritance | `inherit_permissions` | The worker inherits the session's sandbox and approval policy. Writes outside the workspace trigger the host's own approval prompt routed to the user; the adapter never requests broader access on the worker's behalf beyond the parent policy. | `BLOCKED` when an in-scope action needs approval the user has not granted. |
| Lifecycle control | `control_lifecycle` | Continue the same worker with `send_message`; stop the current turn with `interrupt_agent` (already-queued messages stay parked until a later `send_message`); observe state with `list_agents`. Replace a writer only after the previous one is confirmed stopped, completed, or closed. | `BLOCKED` for unresolved ownership; `FAILED` for an unrecoverable host control failure. |
| Progress reporting | `report_progress` | Runtime completion notices and `list_agents`/`job_output` observation relay concise progress to the Planner; raw tool logs remain in the worker's own context. | `FAILED` only when progress and result state cannot be recovered after evidence-based attempts. |
| Result relay | `relay_result` | Receive the worker's final message and validate the exact first line (`STATUS: DONE`, `STATUS: BLOCKED`, or `STATUS: FAILED`) and every required Core section before Planner reporting. | Continue the same worker via `send_message` for an in-scope malformed result; otherwise `FAILED`. Never rewrite status or evidence. |
| Version-control management | `manage_version_control` | Read-only baselines with `git rev-parse`, `git status --short`, `git diff`, and branch/detached inspection. With exact commit authority: `git add` the exact authorized paths only (never `git add .`/`git add -A`), inspect `git diff --cached`, validate the Conventional Commit message, commit, and record the SHA. Push only under separate remote/refspec authority. `version_control_system: none` performs no Git operation. | `BLOCKED` for authority, overlap, or baseline conflicts; `FAILED` for an unrecoverable authorized Git operation. |

## `identify_host`

Preconditions: the workflow skill is loaded in a DSH session. Confirm host identity only from host-provided signals — the native tool surface, the DSH skill catalog entry for this skill, and read-only `$env:DSH_*` inspection — and confirm the active surface is `web-gui`.

Output: `host_id=dsh`, the active surface, and availability evidence for subagent dispatch, permission inheritance, lifecycle observation, and result return.

## `bind_planner`

Bind the current main task without spawning a planning agent. Its deployed model remains the Planner model, and only this task communicates with the user.

Resolve:

- the repository root from the session workspace;
- the Core, adapter, and coding-rule references from the loaded skill's base directory;
- the contract asset from the same skill;
- task records under `.dsh/task-runs/<task-id>/` in the repository.

Creating a task record does not authorize product-code writes, ignore-file changes, staging, commits, or pushes.

## `validate_model`

Accepted selections, in order:

1. `inherit-parent (user-approved)` — the worker inherits the Planner's deployed model; this is the primary supported path.
2. An explicit session reasoning-mode value, only when the user approves it for this task and the contract records it.
3. A distinct exact model id — not representable for subagent dispatch on this surface; return `BLOCKED` with the options instead of substituting.

## `dispatch_worker`

Compose the full Core dispatch envelope into one standalone worker prompt (the worker sees no conversation history): contract location, Core protocol location, task id and revision, model selection, coding-rule component paths, and the three behavioral instructions (contract is sole authority; no user questions, scope expansion, or second writer; exactly one result schema). Dispatch exactly one `subagent`; do not add a reviewer, tester, or explorer.

## `manage_version_control`

Baseline (always read-only): repository root, branch or detached state, current revision, index/staged state, uncommitted paths, and changes to preserve.

With `commit authority: none`: leave the index and `HEAD` untouched and report the proposed Conventional Commit message in the result's `VERSION_CONTROL` section.

With exact commit authority: stage only the contract-listed paths, inspect `git diff --cached`, validate the single logical boundary and message, commit, and record the SHA. Never amend, squash, rebase, tag, or rewrite history without separate authorization.

Push only when the contract separately authorizes the exact remote and refspec; commit authority never implies push authority.

Sandbox note: repository writes stay inside the workspace; any host permission escalation is itself a user-approved, operation-specific act and is recorded as authorization evidence only for the exact operation the user approved.

## Verification checklist

- [ ] Host identification succeeds in a DSH session and rejects identification on a non-DSH host.
- [ ] The current user-facing task remains the only Planner; no planning agent is spawned.
- [ ] Core, contract asset, coding-rule components, repository, and `.dsh/task-runs/` locations resolve from the loaded skill without host-neutral assumptions.
- [ ] `inherit-parent` dispatch works; a distinct exact-model request maps to `BLOCKED` with options and no substitution.
- [ ] Exactly one worker receives the complete dispatch envelope, including the coding-rule component paths, and loads them before its first edit.
- [ ] The worker's sandbox matches the session policy; no broadening occurs without an explicit user-approved operation.
- [ ] `send_message` continuation, `interrupt_agent` interruption, completion, and confirmed-safe replacement are exercised.
- [ ] Progress reaches the Planner without a second writer or raw-log pollution.
- [ ] `DONE`, `BLOCKED`, and `FAILED` are relayed losslessly; a malformed result triggers the in-scope correction path.
- [ ] `version_control_system: none` performs no Git operation; baseline inspection never mutates the repository.
- [ ] Missing commit or push authority prevents the corresponding operation; implementation approval is never treated as authority.
- [ ] An isolated Git fixture proves exact-path staging, staged-diff inspection, a compliant bounded commit, clean post-commit state, and no unapproved push.
- [ ] Separate push authority is checked against the exact remote and refspec without inheriting from commit authority.
- [ ] A missing capability produces `CAPABILITY_UNAVAILABLE` before approval or writes.
- [ ] Retained evidence exists for every claimed surface and version, and an independent review approves promotion to `VERIFIED`.

Until every item has retained evidence and the front matter is updated deliberately, this adapter remains `EXPERIMENTAL` and is selectable only through the explicit user acknowledgement defined at the top of this document.
