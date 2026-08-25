---
host_adapter: "{{HOST_ADAPTER_ID}}"
host_id: "{{HOST_ID}}"
display_name: "{{HOST_DISPLAY_NAME}} Host Adapter"
protocol_version: "0.5"
adapter_version: "{{ADAPTER_VERSION}}"
support_state: "AUTHORING_ONLY"
supported_surfaces:
  - "{{HOST_SURFACE}}"
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

# Host Adapter Authoring Template

Implementation dispatch eligibility: **no**. This `AUTHORING_ONLY` template is never an implementation adapter.

This file is intentionally `AUTHORING_ONLY`. Its placeholders and checklist help an adapter author apply the [Host Adapter Contract](../adapter-contract.md) to the [Core protocol](../protocol.md). It is not executable support, and copying or filling it does not make a host supported.

Keep `support_state: AUTHORING_ONLY` until every required operation has a concrete host mapping and the full verification checklist has independent evidence. Protocol `0.5` permits implementation writes only after a deliberate release marks the adapter `VERIFIED`; neither `AUTHORING_ONLY` nor `EXPERIMENTAL` artifacts can be selected for writes.

## Authoring placeholders

Replace the double-braced metadata values in a derived adapter reference. Record the exact host versions, surfaces, mechanism names, and verification evidence; do not rely on conceptual similarity to another adapter.

## Operation map

| Capability | Operation | Host mapping | Failure mapping |
| --- | --- | --- | --- |
| Host identification | `identify_host` | `{{READ_ONLY_HOST_IDENTITY_MECHANISM}}` | `{{IDENTITY_FAILURE_SIGNAL}}` |
| Planner binding | `bind_planner` | `{{USER_FACING_PLANNER_AND_RESOURCE_RESOLUTION}}` | `{{BINDING_FAILURE_SIGNAL}}` |
| Model validation | `validate_model` | `{{MODEL_AND_REASONING_VALIDATION_MECHANISM}}` | `{{MODEL_FAILURE_SIGNAL}}` |
| Worker dispatch | `dispatch_worker` | `{{SINGLE_WORKER_DISPATCH_MECHANISM}}` | `{{DISPATCH_FAILURE_SIGNAL}}` |
| Permission inheritance | `inherit_permissions` | `{{SANDBOX_AND_APPROVAL_MAPPING}}` | `{{PERMISSION_FAILURE_SIGNAL}}` |
| Lifecycle control | `control_lifecycle` | `{{OWNERSHIP_START_CONTINUE_INTERRUPT_STOP_REPLACE_MAPPING}}` | `{{LIFECYCLE_FAILURE_SIGNAL}}` |
| Progress reporting | `report_progress` | `{{PROGRESS_OBSERVATION_AND_RELAY_MAPPING}}` | `{{PROGRESS_FAILURE_SIGNAL}}` |
| Result relay | `relay_result` | `{{LOSSLESS_FINAL_RESULT_AND_DOCUMENTATION_EVIDENCE_MAPPING}}` | `{{RESULT_FAILURE_SIGNAL}}` |
| Version-control management | `manage_version_control` | `{{READ_ONLY_BASELINE_EXACT_STAGE_COMMIT_AND_SEPARATE_PUSH_MAPPING}}` | `{{VERSION_CONTROL_FAILURE_SIGNAL}}` |

For each section below, replace the authoring prompt with preconditions, exact inputs and outputs, the concrete host mechanism, failure classification, and evidence.

## `identify_host`

`{{HOW_THE_ADAPTER_IDENTIFIES_THE_HOST_AND_SURFACE_WITHOUT_WRITING}}`

## `bind_planner`

`{{HOW_THE_CURRENT_USER_FACING_TASK_REMAINS_PLANNER_AND_RESOLVES_CORE_CONTRACT_AND_TASK_RECORDS}}`

## `validate_model`

`{{HOW_EXACT_USER_APPROVAL_MODEL_AVAILABILITY_REASONING_EFFORT_AND_OPTIONAL_PARENT_INHERITANCE_ARE_VALIDATED}}`

## `dispatch_worker`

`{{HOW_EXACTLY_ONE_WORKER_RECEIVES_THE_COMPLETE_CORE_DISPATCH_ENVELOPE}}`

## `inherit_permissions`

`{{HOW_PARENT_PERMISSIONS_ARE_PRESERVED_OR_NARROWED_AND_NEVER_BROADENED}}`

## `control_lifecycle`

`{{HOW_WRITER_OWNERSHIP_START_CONTINUATION_INTERRUPTION_STOP_COMPLETION_AND_SAFE_REPLACEMENT_WORK}}`

## `report_progress`

`{{HOW_PROGRESS_IS_OBSERVED_WITHOUT_CREATING_ANOTHER_WRITER_OR_POLLUTING_PLANNER_DECISIONS}}`

## `relay_result`

`{{HOW_DONE_BLOCKED_AND_FAILED_MARKDOWN_RESULTS_AND_THEIR_DOCUMENTATION_EVIDENCE_REACH_THE_PLANNER_WITHOUT_REWRITING_STATUS_OR_EVIDENCE}}`

## `manage_version_control`

`{{HOW_NONE_AND_GIT_SYSTEMS_ARE_HANDLED_READ_ONLY_BY_DEFAULT_AND_HOW_EXACT_CONTRACT_AUTHORITY_MAPS_TO_STAGING_COMMIT_AND_SEPARATE_PUSH}}`

Document the host's read-only baseline commands, exact-path staging mechanism, staged-diff inspection, Conventional Commit validation, post-commit evidence, and separate remote/refspec push gate. The mapping must preserve the index and `HEAD` when authority is `none`, preserve unrelated changes when authority is granted, and classify authority or overlap conflicts as `BLOCKED` before mutation.

## Verification checklist

- [ ] Host identification succeeds on every claimed surface and rejects a different host.
- [ ] The current user-facing task remains the only Planner.
- [ ] Core, contract asset, repository, and task-record locations resolve without host-neutral Core assumptions.
- [ ] Valid and invalid model choices are tested, including explicit parent inheritance when claimed.
- [ ] Exactly one worker receives the complete dispatch envelope and approved model mapping.
- [ ] Sandbox and approval policies are preserved or narrowed, never broadened.
- [ ] Writer ownership, interruption, continuation, completion, and replacement are exercised.
- [ ] Progress can be observed without another writer or loss of final state.
- [ ] `DONE`, `BLOCKED`, and `FAILED` are relayed losslessly, including every `DOCUMENTATION` field.
- [ ] `version_control_system: none` performs no Git operation, and Git baseline inspection does not mutate the repository.
- [ ] Missing commit or push authority prevents the corresponding operation; implementation approval is not treated as authority.
- [ ] An isolated Git fixture proves exact-path staging, staged-diff inspection, a compliant bounded commit, clean post-commit state, and no unapproved push.
- [ ] Separate push authority is checked against the exact remote and refspec without inheriting from commit authority.
- [ ] Missing capabilities and every non-`VERIFIED` support state produce `CAPABILITY_UNAVAILABLE` before approval or writes.
- [ ] Every claimed host surface and version has retained evidence.
- [ ] An independent review approves promotion to `VERIFIED`.

Until every item has evidence and metadata is updated deliberately to a versioned `VERIFIED` release, this reference remains `AUTHORING_ONLY` and must not be selected for implementation.
