---
host_adapter: "zcode"
host_id: "zcode"
display_name: "ZCode Host Adapter"
protocol_version: "0.6"
adapter_version: "0.1"
support_state: "EXPERIMENTAL"
supported_surfaces:
  - "cli"
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
verified_on: null
---

# ZCode Host Adapter

Implementation dispatch eligibility: **no**. While `support_state` is `EXPERIMENTAL`, this artifact may be inspected and validated but cannot authorize or dispatch product writes.

This reference records a candidate ZCode mapping for the [Host Adapter Contract](../adapter-contract.md) and the [Core protocol](../protocol.md) with the [Context Routing reference](../context-routing.md). The operation designs have not been exercised end to end with retained evidence on the claimed surface. Promotion to `VERIFIED` requires the full adapter-contract verification checklist, retained evidence, and a deliberate versioned metadata change.

## Why this adapter exists

ZCode is the most likely interactive coding-agent host for this workflow: its built-in Agent tool offers a general-purpose subagent type and an `Explore` subagent type that is read-only by design. The `Explore` type maps naturally onto the optional `read_only_scout_dispatch` capability, because the host itself enforces the read-only scope rather than relying on prompt discipline.

## Compatibility (candidate)

| Item | Candidate mapping |
| --- | --- |
| Core protocol | Exact version `0.6` |
| Adapter | `zcode` version `0.1` |
| Planner | Current ZCode main task and its selected model |
| Worker | One general-purpose subagent via the Agent tool, only after promotion |
| Scout | `Explore` subagent via the Agent tool, read-only by host design |
| Contract asset | Loaded Skill's `assets/implementation-contract.md` |
| Task records | Repository-local `.zcode/task-runs/<task-id>/implementation-contract-v<revision>.md` |
| Result schemas | Core `DONE`, `BLOCKED`, and `FAILED` Markdown schemas with `DOCUMENTATION` evidence; scouts return evidence packets |

## Operation map (candidate)

| Capability | Operation | Candidate ZCode mechanism | Current failure mapping |
| --- | --- | --- | --- |
| Host identification | `identify_host` | Confirm ZCode from host-provided session and tool metadata without writing. | `CAPABILITY_UNAVAILABLE` if identity is absent or ambiguous. |
| Planner binding | `bind_planner` | Keep the main task as Planner; resolve loaded resources and repository-local task records. | `CAPABILITY_UNAVAILABLE` if resources cannot be resolved. |
| Model validation | `validate_model` | ZCode subagents do not expose per-dispatch model overrides in the current CLI; record the parent model as the only representable selection until a model-override surface is verified. | `CAPABILITY_UNAVAILABLE` for implementation while this adapter is not verified. |
| Worker dispatch | `dispatch_worker` | One general-purpose Agent-tool subagent with the complete Core envelope. | Do not call; return `CAPABILITY_UNAVAILABLE` before writes. |
| Permission inheritance | `inherit_permissions` | Subagents inherit the session sandbox and permission mode; the permission system mediates tool calls. | Do not exercise for product writes before promotion. |
| Lifecycle control | `control_lifecycle` | Agent-tool task lifecycle (background execution, TaskOutput, TaskStop) with single-writer ownership confirmed before spawn. | Do not start a writer; incomplete retained evidence prevents dispatch. |
| Progress reporting | `report_progress` | Observe subagent progress via TaskOutput while raw logs remain with the worker. | Validation artifacts only until promotion. |
| Result relay | `relay_result` | Subagent final message validated against the Core result schemas, including `DOCUMENTATION`. | Validation artifacts only until promotion. |
| Version-control management | `manage_version_control` | Read-only Git baseline inspection; exact-path staging and commit only under contract authority. | Read-only artifact validation only. |
| Read-only scout dispatch (optional) | `dispatch_scout` | One `Explore`-type subagent per scout task packet; the host enforces read-only access; evidence packets returned as the subagent final message. | `CAPABILITY_UNAVAILABLE` until this adapter is promoted; until then the Planner uses the fast lane. |

## Verification checklist (blocking promotion)

- positive host identification and rejection on a different host;
- model selection representability: confirm whether any per-subagent model override surface exists; without one, document parent-model-only scouting and its cost implications explicitly in the proposal;
- single-writer dispatch with the full envelope, including coding-rule paths;
- read-only scout dispatch with an `Explore` subagent, confirming the host rejects any write attempt and the evidence packet survives the subagent boundary;
- interruption, continuation, completion, and safe replacement through TaskOutput/TaskStop;
- lossless relay of all three result schemas;
- the full Git fixture checklist from the Host Adapter Contract;
- capability-unavailable behavior before writes for this `EXPERIMENTAL` state.

Until every item is exercised with retained evidence, any write dispatch attempt fails before product changes with `CAPABILITY_UNAVAILABLE`.
