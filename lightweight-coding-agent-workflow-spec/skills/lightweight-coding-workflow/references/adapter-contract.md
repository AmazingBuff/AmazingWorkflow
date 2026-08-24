# Host Adapter Contract

Contract version: `0.4`.

This reference defines the interface between the host-neutral [Core protocol](protocol.md) and a host-specific adapter. An adapter is an instruction mapping, not a new runtime or dependency.

## Required metadata

Every adapter reference begins with machine-readable YAML front matter containing:

| Field | Requirement |
| --- | --- |
| `host_adapter` | Stable adapter id used in implementation contracts. |
| `host_id` | Stable id returned by host identification. |
| `display_name` | Human-readable host and adapter name. |
| `protocol_version` | Core protocol version implemented by the adapter. |
| `adapter_version` | Version of the mapping itself. |
| `support_state` | One of `VERIFIED`, `EXPERIMENTAL`, `AUTHORING_ONLY`, or `UNSUPPORTED`. |
| `supported_surfaces` | Host surfaces for which the mapping was verified or authored. |
| `capabilities` | The complete set of required capability ids below. |
| `verified_on` | Verification date for `VERIFIED`, otherwise `null`. |

Adapter ids and versions are immutable inputs to an approved contract. Changing either requires a new contract revision.

## Required capabilities and operations

An eligible adapter declares every capability exactly once and maps its operation to a concrete host mechanism.

| Capability id | Required operation | Required outcome |
| --- | --- | --- |
| `host_identification` | `identify_host` | Determine the active host and surface without writing. |
| `planner_binding` | `bind_planner` | Bind the current user-facing task as Planner and resolve protocol, contract-asset, repository, and task-record locations. |
| `model_validation` | `validate_model` | Validate the exact user-approved model and optional reasoning effort, including explicit parent inheritance when supported. |
| `worker_dispatch` | `dispatch_worker` | Start exactly one implementation worker with the Core dispatch envelope and approved model mapping. |
| `permission_inheritance` | `inherit_permissions` | Preserve or narrow the parent task's sandbox and approval policy without escalation by configuration. |
| `lifecycle_control` | `control_lifecycle` | Determine writer ownership and start, continue, interrupt, stop, or replace a worker safely. |
| `progress_reporting` | `report_progress` | Observe worker progress while keeping raw implementation output out of the Planner's decision context. |
| `result_relay` | `relay_result` | Return exactly one Core `DONE`, `BLOCKED`, or `FAILED` result to the Planner without loss or status rewriting. |
| `version_control_management` | `manage_version_control` | Inspect version-control state without mutation by default, and perform only contract-authorized staging, commit, and separately authorized push operations. |

Each operation mapping states:

- preconditions;
- host mechanism and exact identifiers where relevant;
- inputs and outputs;
- failure signal;
- whether failure is `CAPABILITY_UNAVAILABLE`, `BLOCKED`, or `FAILED` under the Core rules;
- evidence used to claim the adapter's support state.

Documentation, pseudocode, or an untested guess is not a concrete mapping for `VERIFIED` status.

## Support states

| State | Meaning | Eligible for implementation writes |
| --- | --- | --- |
| `VERIFIED` | Every required operation is mapped and has been exercised on every claimed surface for the declared versions. | Yes, after approval and capability revalidation. |
| `EXPERIMENTAL` | A runnable mapping exists but verification is incomplete or limited. | Only when the user explicitly approves that named adapter and its state in the same approval that grants the contract, which records the acknowledged state. |
| `AUTHORING_ONLY` | A structured template or design aid exists; no runnable support is claimed. | No. |
| `UNSUPPORTED` | One or more required operations have no acceptable host mapping. | No. |

Only `VERIFIED` adapters are selected by default; an `EXPERIMENTAL` adapter becomes selectable solely through the explicit user acknowledgement defined above. A host does not become supported merely because its concepts resemble another host or because an authoring template was copied.

## Selection and validation

The Planner performs this read-only gate before requesting implementation approval, writing an approved contract, or allowing product-code writes:

1. Call the candidate mapping's `identify_host` logic using host-provided signals.
2. Collect adapter references whose `host_id` exactly matches the identified host and whose claimed surface contains the active surface.
3. Require exactly one matching adapter with `support_state: VERIFIED`; an `EXPERIMENTAL` match additionally requires the user's explicit named acknowledgement recorded in the approved contract.
4. Require exact Core compatibility for `protocol_version` unless a documented compatibility range exists.
5. Require a non-empty `adapter_version` and all nine capability ids.
6. Read every operation mapping and confirm that its required host mechanism is available in the current task.
7. Record `host_adapter` and `adapter_version` in the proposal and approved contract.
8. Repeat capability and version validation immediately before worker dispatch.

Protocol `0.4` documents this compatibility range: it is additive over `0.3` — an optional `Applicable coding rules` contract section, matching dispatch-envelope entries, and the explicit `EXPERIMENTAL` selection path — so an adapter verified under `0.3` remains eligible under Core `0.4` without re-verification.

Selection is per task. Never merge two partial adapters, select an adapter by filename alone, or fall back to an ineligible state.

## Failure behavior

Return `CAPABILITY_UNAVAILABLE` and stop before approval or writes when:

- the host or active surface cannot be identified;
- no adapter matches;
- multiple verified adapters match;
- the only matching adapter is `AUTHORING_ONLY` or `UNSUPPORTED`, or is `EXPERIMENTAL` without the user's explicit named acknowledgement;
- protocol or adapter metadata is missing or incompatible;
- any required capability or host mechanism is unavailable;
- model validation or worker dispatch cannot be represented faithfully.

The capability report names the host, candidate adapters, failed operation, and observed evidence. It must not dispatch a generic worker, borrow another host's mapping, or let the Planner implement as a fallback.

After an approved implementation has started, use the Core result states: `BLOCKED` for a user decision, authority, permission, or contract revision; `FAILED` for an evidence-backed environmental or execution failure that cannot progress under the same conditions.

## Verification and promotion

Before setting `support_state: VERIFIED`, exercise all required operations on each claimed surface and retain evidence for:

- positive host identification and rejection on a different host;
- Planner identity and user-facing ownership;
- valid, invalid, and explicit-inheritance model selections;
- single-worker dispatch with the full envelope;
- sandbox and approval-policy preservation;
- interruption, continuation, completion, and safe replacement;
- progress observation without a second writer;
- lossless relay of all three result schemas;
- non-mutating handling for `version_control_system: none` and read-only Git baseline inspection;
- rejection of staging, commit, and push when their exact authorities are absent;
- exact-path staging, staged-diff inspection, a compliant commit, clean post-commit state, and separately authorized push handling in an isolated Git fixture;
- capability-unavailable behavior before writes.

Use [adapters/template.md](adapters/template.md) to author a mapping. Its `AUTHORING_ONLY` state is intentional and cannot be promoted without the evidence above.
