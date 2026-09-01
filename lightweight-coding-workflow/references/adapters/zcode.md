---
host_adapter: "zcode"
host_id: "zcode"
display_name: "ZCode Host Adapter"
protocol_version: "0.6"
adapter_version: "0.2"
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

This reference records a candidate ZCode mapping for the [Host Adapter Contract](../adapter-contract.md) and the [Core protocol](../protocol.md) with the [Context Routing reference](../context-routing.md). The operation designs follow the official ZCode subagent documentation but have not been exercised end to end with retained evidence on the claimed surface. Promotion to `VERIFIED` requires the full adapter-contract verification checklist, retained evidence, and a deliberate versioned metadata change.

## Why this adapter exists

ZCode is the most likely interactive coding-agent host for this workflow: its built-in Agent tool offers a general-purpose subagent type and an `Explore` subagent type that is read-only by design. The `Explore` type maps naturally onto the optional `read_only_scout_dispatch` capability, because the host itself enforces the read-only scope rather than relying on prompt discipline.

ZCode binds a subagent's model at the definition level, not at dispatch time. User-scope agent definitions under `~/.zcode/agents/<name>.md` carry a `model` frontmatter field (a specific model, `inherit`, or empty), and even the built-in agents can carry a separately configured model and thought level. This per-definition binding is how the adapter represents the Core's explicit, user-approved model selection: choosing the approved model means dispatching the agent type whose definition binds it.

## Compatibility (candidate)

| Item | Candidate mapping |
| --- | --- |
| Core protocol | Exact version `0.6` |
| Adapter | `zcode` version `0.2` |
| Planner | Current ZCode main task and its selected model |
| Worker | One Agent-tool subagent of the agent type that binds the approved model: the custom `lightweight_implementer` definition for an exact model, or an unbound type for approved parent inheritance; only after promotion |
| Scout | `Explore` subagent with the approved scout model bound to that agent type, or a custom read-only `lightweight_scout` definition binding that model |
| Model binding | Per agent definition (`model` field in `~/.zcode/agents/<name>.md`); the Agent tool exposes no per-dispatch model override |
| Agent definitions | `~/.zcode/agents/<name>.md`, Markdown body as the system prompt, user scope only in the current Beta; Codex-style `agents/*.toml` files from this package are not read by ZCode and need Markdown equivalents |
| Contract asset | Loaded Skill's `assets/implementation-contract.md` |
| Task records | Repository-local `.zcode/task-runs/<task-id>/implementation-contract-v<revision>.md` |
| Result schemas | Core `DONE`, `BLOCKED`, and `FAILED` Markdown schemas with `DOCUMENTATION` evidence; scouts return evidence packets |

## Operation map (candidate)

| Capability | Operation | Candidate ZCode mechanism | Current failure mapping |
| --- | --- | --- | --- |
| Host identification | `identify_host` | Confirm ZCode from host-provided session and tool metadata without writing. | `CAPABILITY_UNAVAILABLE` if identity is absent or ambiguous. |
| Planner binding | `bind_planner` | Keep the main task as Planner; resolve loaded resources and repository-local task records. | `CAPABILITY_UNAVAILABLE` if resources cannot be resolved. |
| Model validation | `validate_model` | Confirm an agent definition loaded in the current session binds the exact user-approved model, or that the dispatched type has no binding for approved parent inheritance; see `validate_model` below. | Return to planning when no loaded agent type binds the approved selection; `CAPABILITY_UNAVAILABLE` for implementation while this adapter is not verified. |
| Worker dispatch | `dispatch_worker` | One Agent-tool subagent of the model-bound agent type with the complete Core envelope. | Do not call; return `CAPABILITY_UNAVAILABLE` before writes. |
| Permission inheritance | `inherit_permissions` | Subagents inherit the session sandbox and permission mode; the permission system mediates tool calls. | Do not exercise for product writes before promotion. |
| Lifecycle control | `control_lifecycle` | ZCode Agent-tool lifecycle surface; persistent continuation, interruption, and replacement controls remain unresolved pending live host-tool-schema evidence. | Do not start a writer; incomplete retained evidence prevents dispatch. |
| Progress reporting | `report_progress` | ZCode task-state/progress surface; exact observation and persistence behavior remain unresolved pending live host-tool-schema evidence. | Validation artifacts only until promotion. |
| Result relay | `relay_result` | Subagent final message validated against the Core result schemas, including `DOCUMENTATION`. | Validation artifacts only until promotion. |
| Version-control management | `manage_version_control` | Read-only Git baseline inspection; exact-path staging and commit only under contract authority. | Read-only artifact validation only. |
| Read-only scout dispatch (optional) | `dispatch_scout` | One `Explore`-type subagent per scout task packet, with the approved scout model bound to that agent type; the host enforces read-only access; evidence packets returned as the subagent final message. | `CAPABILITY_UNAVAILABLE` until this adapter is promoted; until then the Planner uses the fast lane. |

Persistent continuation, interruption, completion, and safe replacement are not
claimed mappings: their exact controls and request/response schema remain
unresolved until exercised against a live ZCode host tool schema.

## `validate_model` (candidate)

ZCode resolves a subagent's model from its agent definition, not from the dispatch call. Per the official subagent documentation, the effective model comes from the `model` frontmatter field of the dispatched agent's definition under `~/.zcode/agents/<name>.md` — a specific model id, `inherit`, or empty — while built-in agents (`general-purpose`, `Explore`) inherit the parent model unless a model is separately configured for that built-in. An unset model follows the main session's model, including after a mid-session model switch.

The Agent tool exposes no per-dispatch model parameter, so an approved model selection is representable only as an agent type that binds it. Validation therefore:

1. For an exact user-approved model, confirm that an agent definition loaded in the current session binds exactly that model, then dispatch that agent type. If no loaded definition binds it, return to planning with the set of representable models; creating a new binding definition is a planning-time proposal, and because agent definitions load only at session start, the user must start a new session before the new type becomes dispatchable.
2. For `inherit-parent (user-approved)`, confirm the dispatched type has no model binding (empty or `inherit`, or an unconfigured built-in) so the parent's model is the effective selection.
3. A project default is valid only after the user explicitly approves its exact effective value for the current task.

The optional reasoning effort maps to the definition's `thoughtLevel` field, which is honored only when a specific model is set. Model and `thoughtLevel` changes take effect in new sessions only; a running session does not hot-reload definitions.

If the approved selection cannot be represented by a loaded agent type, return to planning. Do not silently dispatch a differently modeled type and do not fall back to another value. The Core dispatch envelope still records the adapter-validated model selection; under ZCode it informs the worker of its bound model rather than overriding anything.

## Verification checklist (blocking promotion)

- positive host identification and rejection on a different host;
- model selection representability: exercise per-definition model binding (`model` and `thoughtLevel`) on a custom agent and on a built-in agent, confirm definitions load only at session start, and confirm dispatching the bound type runs the approved model; confirm no per-dispatch override surface exists so an unrepresentable selection returns to planning;
- single-writer dispatch with the full envelope, including coding-rule paths;
- read-only scout dispatch with a scout agent binding the approved cheap model, confirming the host rejects any write attempt and the evidence packet survives the subagent boundary;
- live host-tool-schema exercise of persistence, continuation, interruption, completion, and safe replacement, with retained evidence before any of those behaviors are claimed;
- lossless relay of all three result schemas;
- the full Git fixture checklist from the Host Adapter Contract;
- capability-unavailable behavior before writes for this `EXPERIMENTAL` state.

Until every item is exercised with retained evidence, any write dispatch attempt fails before product changes with `CAPABILITY_UNAVAILABLE`.
