---
host_adapter: "dsh"
host_id: "dsh"
display_name: "DeepSeek Harness Host Adapter"
protocol_version: "0.5"
adapter_version: "0.5"
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

Implementation dispatch eligibility: **no**. While `support_state` is `EXPERIMENTAL`, this artifact may be inspected and validated but cannot authorize or dispatch product writes.

This reference records a candidate DeepSeek Harness (DSH) mapping for the [Host Adapter Contract](../adapter-contract.md) and [Core protocol](../protocol.md). The nine operation designs have not been exercised end to end with retained evidence on the claimed surface. Protocol `0.5` permits implementation dispatch only through a `VERIFIED` adapter, so no user decision or approved contract can select this mapping for writes.

Promotion requires every item in the [verification checklist](#verification-checklist), retained evidence, independent review, and a deliberate versioned metadata change. Until then, every attempted write dispatch fails before product changes with `CAPABILITY_UNAVAILABLE`.

## Compatibility

| Item | Candidate mapping |
| --- | --- |
| Core protocol | Exact version `0.5` |
| Adapter | `dsh` version `0.5` |
| Planner | Current DSH main task and its deployed model |
| Worker | One isolated DSH background subagent, only after promotion |
| Contract asset | Loaded Skill's `assets/implementation-contract.md` |
| Feature documentation | Loaded convention and template plus contract-selected repository paths |
| Coding-rule components | Loaded Skill's `assets/coding-rules/**`, listed by absolute path in the contract |
| Task records | Repository-local `.dsh/task-runs/<task-id>/implementation-contract-v<revision>.md` |
| Result schemas | Core `DONE`, `BLOCKED`, and `FAILED` Markdown schemas with `DOCUMENTATION` evidence |

## Operation map

| Capability | Operation | Candidate DSH mechanism | Current failure mapping |
| --- | --- | --- | --- |
| Host identification | `identify_host` | Confirm DSH from host-provided tool, Skill-catalog, and session signals without writing. | `CAPABILITY_UNAVAILABLE` if identity is absent or ambiguous. |
| Planner binding | `bind_planner` | Keep the main task as Planner and resolve loaded resources plus repository-local task records. | `CAPABILITY_UNAVAILABLE` if resources cannot be resolved. |
| Model validation | `validate_model` | Validate parent inheritance and any representable session reasoning mode. | `CAPABILITY_UNAVAILABLE` for implementation while this adapter is not verified. |
| Worker dispatch | `dispatch_worker` | Candidate native isolated-subagent call with the complete Core envelope. | Do not call; return `CAPABILITY_UNAVAILABLE` before writes. |
| Permission inheritance | `inherit_permissions` | Candidate inheritance of the session sandbox and approval policy. | Do not exercise for product writes before promotion. |
| Lifecycle control | `control_lifecycle` | Candidate ownership, continuation, interruption, stop, and replacement controls. | Do not start a writer; incomplete retained evidence prevents dispatch. |
| Progress reporting | `report_progress` | Candidate native state and output observation without a second writer. | Validation artifacts only until promotion. |
| Result relay | `relay_result` | Candidate lossless return and schema validation, including `DOCUMENTATION`. | Validation artifacts only until promotion. |
| Version-control management | `manage_version_control` | Candidate read-only baseline plus separately authorized exact staging, commit, and push handling. | Read-only artifact validation only; no product-write workflow. |

## `identify_host`

Candidate preconditions: the workflow Skill is loaded in a DSH session. Confirm host identity only from host-provided signals—the native tool surface, DSH Skill catalog, and read-only `DSH_*` session metadata—and confirm the active surface is `web-gui`. Do not infer DSH from repository files or this adapter's presence.

Output for promotion testing: `host_id=dsh`, the active surface, and availability evidence for subagent dispatch, permission inheritance, lifecycle observation, result return, and version-control management. Identity does not make the adapter write-eligible.

## `bind_planner`

Candidate mapping: bind the current main task without spawning a planning agent. Resolve the repository root from the workspace; resolve the Core, Adapter Contract, feature-documentation resources, coding-rule resources, and contract asset from the loaded Skill; resolve task records under `.dsh/task-runs/<task-id>/`.

Creating or locating a task record does not authorize implementation, ignore-file changes, staging, commits, or pushes. Under the current support state, stop before creating an implementation contract that names this adapter.

## `validate_model`

Candidate representable values are explicit parent inheritance and an explicitly selected session reasoning mode. A distinct exact subagent model is not representable on the authored surface and would require returning to planning rather than substitution.

Current protocol action: report `CAPABILITY_UNAVAILABLE` for implementation because model representability cannot override the support-state gate. Model validation may be exercised only in an isolated promotion fixture with no product writes.

## `dispatch_worker`

The candidate promoted implementation would compose one standalone worker prompt containing the absolute contract and Core paths, task id and revision, approved model selection, applicable coding-rule paths, Documentation obligations, single-writer limits, and exact result-schema instruction, then call the native isolated-subagent mechanism once.

Current protocol action: MUST NOT call the candidate dispatch mechanism. Return `CAPABILITY_UNAVAILABLE` before any writer starts. Filling the contract, obtaining user consent, or verifying only part of the checklist cannot change this action.

## `inherit_permissions`

The candidate promoted worker would inherit or narrow the session sandbox and approval policy and would never broaden access by configuration. Operation-specific elevation would remain subject to the parent host's policy.

Current protocol action: do not start a product writer, so no implementation permission inheritance occurs. Promotion tests use isolated fixtures and retain evidence that parent policy is preserved.

## `control_lifecycle`

The candidate mapping uses native ownership and state inspection, continuation messaging, interruption, stop, completion, and confirmed-safe replacement. A replacement would be allowed only after the previous writer is stopped, completed, or closed.

Current protocol action: because no writer may start, lifecycle controls are limited to isolated promotion tests. Any attempted product implementation stops at the write gate.

## `report_progress`

The candidate mapping observes native completion notices and worker state/output, keeps raw logs in the worker context, and relays concise progress to the Planner without another writer.

Current protocol action: no product implementation is running, so only isolated promotion evidence may exercise progress reporting.

## `relay_result`

The candidate mapping receives one final result and validates the exact status line, all status-specific Core sections, command and acceptance evidence, and the complete `DOCUMENTATION` decision, navigation, validation, and freshness evidence. It never rewrites status.

Current protocol action: result relay can be tested with isolated synthetic results, but it does not make product dispatch eligible.

## `manage_version_control`

The candidate mapping records repository root, branch or detached state, revision, index/staged state, uncommitted paths, and preserved changes with read-only commands. A promoted mapping would leave index and `HEAD` unchanged when commit authority is `none`, stage only exact authorized paths under explicit commit authority, inspect the staged diff, and treat push as a separately authorized remote/refspec operation.

Current protocol action: artifact inspection may verify read-only behavior in an isolated repository. Do not use this adapter to stage, commit, push, or otherwise manage a product implementation.

## Verification checklist

- [ ] Host identification succeeds in a DSH session and rejects identification on a non-DSH host.
- [ ] The current user-facing task remains the only Planner; no planning agent is spawned.
- [ ] Core, contract asset, feature-documentation resources, coding-rule components, repository, and task-record locations resolve from the loaded Skill.
- [ ] Parent-inheritance validation works, and an unrepresentable exact-model request fails without substitution.
- [ ] The non-`VERIFIED` write gate returns `CAPABILITY_UNAVAILABLE` before any product writer starts.
- [ ] In an isolated fixture, exactly one worker receives the complete dispatch envelope and loads coding-rule paths before editing.
- [ ] The isolated worker's sandbox matches the session policy and never broadens it.
- [ ] Continuation, interruption, completion, and confirmed-safe replacement are exercised in isolation.
- [ ] Progress reaches the Planner without a second writer or raw-log pollution.
- [ ] `DONE`, `BLOCKED`, and `FAILED`, including `DOCUMENTATION`, are relayed losslessly; malformed results follow the correction path.
- [ ] `version_control_system: none` performs no Git operation, and baseline inspection never mutates the repository.
- [ ] Missing commit or push authority prevents the corresponding operation.
- [ ] An isolated Git fixture proves exact-path staging, staged-diff inspection, a compliant bounded commit, clean post-commit state, and no unapproved push.
- [ ] Separate push authority is checked against the exact remote and refspec.
- [ ] A missing capability produces `CAPABILITY_UNAVAILABLE` before approval or writes.
- [ ] Package validation, bundled-rule integrity, and source/install parity pass for the promoted release.
- [ ] Retained evidence exists for every claimed surface and version, and an independent review approves promotion.

Until every item has retained evidence and metadata is deliberately released as `VERIFIED`, this adapter remains `EXPERIMENTAL` and ineligible for implementation writes.
