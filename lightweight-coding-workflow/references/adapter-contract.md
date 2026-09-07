# Host Adapter Contract

Contract version: `0.7`.

This reference defines the interface between the host-neutral [Core
protocol](protocol.md) and a host-specific adapter. An adapter is an
instruction mapping, not a new runtime or dependency. It maps the two public
control phases `PLAN` and `WORK`; no adapter Agent owns an entire phase.

## Required metadata

Every adapter reference begins with machine-readable YAML front matter
containing:

| Field | Requirement |
| --- | --- |
| `host_adapter` | Stable adapter id used in implementation contracts. |
| `host_id` | Stable id returned by host identification. |
| `display_name` | Human-readable host and adapter name. |
| `protocol_version` | Exact Core protocol version implemented by the adapter. |
| `adapter_version` | Version of the mapping itself. |
| `support_state` | One of `VERIFIED`, `EXPERIMENTAL`, `AUTHORING_ONLY`, or `UNSUPPORTED`. |
| `supported_surfaces` | Host surfaces for which the mapping was verified or authored. |
| `capabilities` | The complete set of nine required capabilities below. |
| `optional_capabilities` | Optional capability ids, when a mapping is separately verified. |
| `verified_on` | Verification date for `VERIFIED`, otherwise `null`. |

Adapter ids and versions are immutable inputs to an approved contract. Changing
either requires a new contract revision. A `VERIFIED` adapter may omit the
optional PLAN-task capability; omission means direct PLAN handling on that
host, not a missing WORK capability.

## Two-phase and task-capability binding

The Core exposes exactly two public control phases:

1. `PLAN` — the main Planner interprets requirements, chooses direct/micro/
   batch routing, obtains approval, and reports to the user. Direct inspection
   and optional read-only task Agents are activities inside PLAN.
2. `WORK` — one approved implementation task Agent owns all product-code
   writes, verification, and in-scope repair until ownership is released.

Agents are assigned by task capability, not phase ownership. PLAN Evidence Task
Agents use the stable `lightweight_scout` id and accept exactly these kinds:

- `requirement-research`
- `repository-read`
- `dependency-check`
- `evidence-analysis`

The separate WORK capability is `implementation`. A PLAN task is valid only
when it has one independently describable objective, exact source selectors or
query, a budget, stop conditions, a model override, and the Evidence Packet
response contract. The main Planner remains the only decision maker and the
only user-facing agent.

## Required capabilities and operations

An adapter artifact declares every required capability exactly once and maps
its operation to a concrete host mechanism or, for a non-`VERIFIED` artifact,
a candidate mechanism that cannot be executed for product writes.

| Capability id | Required operation | Required outcome |
| --- | --- | --- |
| `host_identification` | `identify_host` | Determine the active host and surface without writing. |
| `planner_binding` | `bind_planner` | Bind the current user-facing task as Planner and resolve protocol, contract-asset, repository, and task-record locations. |
| `model_validation` | `validate_model` | Validate the exact user-approved model and optional reasoning effort, including explicit PLAN-task overrides and parent inheritance when supported. |
| `worker_dispatch` | `dispatch_worker` | Start exactly one implementation worker with the Core WORK dispatch envelope and approved model mapping. |
| `permission_inheritance` | `inherit_permissions` | Preserve or narrow the parent task's sandbox and approval policy without escalation by configuration. |
| `lifecycle_control` | `control_lifecycle` | Determine writer ownership and start, continue, interrupt, stop, or replace a WORK worker safely. |
| `progress_reporting` | `report_progress` | Observe worker progress while keeping raw implementation output out of the Planner's decision context. |
| `result_relay` | `relay_result` | Return exactly one Core `DONE`, `BLOCKED`, or `FAILED` result, including `DOCUMENTATION` evidence, without loss or status rewriting. |
| `version_control_management` | `manage_version_control` | Inspect version-control state without mutation by default, and perform only contract-authorized staging, commit, and separately authorized push operations. |

The optional metadata id `read_only_scout_dispatch` is retained for
compatibility with earlier adapter artifacts. In Protocol 0.7 its operation
is task-scoped PLAN Evidence dispatch, not a general-purpose Scout or planning
worker:

| Capability id | Optional operation | Required task-scoped outcome |
| --- | --- | --- |
| `read_only_scout_dispatch` | `dispatch_scout` | Start one or more exact micro/batch PLAN task envelopes with an explicit validated model override, exact source selectors/query, budgets, stop conditions, and no complete parent transcript; enforce read-only permissions and relay validated Evidence Packets without granting writes, decisions, contract authority, user interaction, or spawn authority. |

An adapter without `read_only_scout_dispatch` remains fully valid and uses
direct PLAN handling. The capability must never be inferred from
`worker_dispatch`, the presence of `lightweight_scout`, or documentation alone.

The optional metadata id `managed_web_research` identifies a separate managed,
read-only web-research capability. It is not implied by
`read_only_scout_dispatch`, a browser, or documentation. A declared mapping may
accept only `requirement-research` or `dependency-check` tasks and must preserve
`shell_network=false` and `external_mutations=false`; it grants no download,
remote-code execution, authentication, dependency-change, copy, GitHub-write,
or other external-mutation authority. A host mapping is `available` only after
a bounded live read-only forward test. Otherwise the capability is recorded as
unavailable and PLAN uses direct Planner search, an explicit uncertain fallback,
or `BLOCKED` according to the research gate.

## PLAN routing and authorization

PLAN routing records one of `direct`, `micro`, or `batch` using the
context-economics record defined by [Context Routing](context-routing.md).
Delegation requires a bounded, independently describable task and either
Planner-context savings above coordination overhead or positive weighted-cost
savings. The record includes Planner-context savings, delegated input tokens,
estimated result size, coordination overhead, and weighted-cost rationale. It
must not claim total-token savings without measured evidence.

`direct` creates no task packet. `micro` carries one task in the minimal
micro-task envelope and does not require a full orchestration plan. `batch`
uses the full validated plan, dependency layers, task packets, and Evidence
Packet merge for multiple independent tasks or information boundaries.

Within the pre-authorized Codex PLAN policy, an adapter may dispatch only when
the validated envelope records:

- `model: "gpt-5.6-luna"` and `reasoning_effort: "max"`;
- an explicit per-task model override with the same values;
- `max_concurrent_tasks: 2` (no more than two concurrent read-only tasks);
- no more than 12,000 estimated input tokens per PLAN round;
- `pass_parent_transcript: false`;
- read-only sandbox, `allow_writes: false`, and
  `allow_external_mutations: false`;
- one user-visible dispatch notice and
  `per_task_approval_required: false`; and
- exact task count and token ceiling in `plan_task_authorization`.

Exceeding any policy limit requires explicit user approval or direct PLAN
fallback. A same-version adapter may narrow the policy but may not broaden it.

## Optional PLAN-task operation contract

When `read_only_scout_dispatch` is declared, `dispatch_scout` has these
preconditions:

1. the host and active surface are identified and the adapter is eligible for
   the selected operation;
2. routing is a validated `micro` or `batch` PLAN envelope;
3. `plan_task_authorization.authorized` is `true`, the exact model and effort
   are present, the task count matches, and the token ceiling is within policy;
4. each task has a supported task kind, exact assigned source descriptors or
   query, explicit model override, budget, stop conditions, and the Evidence
   Packet response contract; and
5. the host enforces a read-only sandbox and does not receive the complete
   parent transcript.

The operation returns one Evidence Packet per task. The packet uses schema
`2.1`, `packet_type: "subagent-result"`, a matching task kind, and these exact
response requirements:

- finding severity: `low`, `medium`, `high`, or `critical`;
- finding confidence: `low`, `medium`, or `high`;
- fact fields: `id`, `statement`, `provenance`, and `confidence`; and
- fact confidence: `confirmed`, `inferred`, or `unverified`;
- external source fields: source kind, direct URL, repository/project,
  revision, retrieval date, license/reuse status, target applicability,
  locator, confidence, and conflicts; and
- research result fields: status, mode, limitations, uncertainty, conflicts,
  and conflict resolution.

The Evidence Packet validator remains authoritative and rejects unsupported
values, missing required fields, mismatched source ids, forbidden expansion,
or any write/decision/contract/spawn authority. A failed read-only operation
returns its host-specific capability failure; it never falls back to a writer.

## Operation mapping requirements

Each operation mapping states:

- preconditions;
- host mechanism and exact identifiers where relevant;
- inputs and outputs;
- failure signal;
- whether failure is `CAPABILITY_UNAVAILABLE`, `BLOCKED`, or `FAILED` under
  the Core rules; and
- evidence used to claim the adapter's support state.

Documentation, pseudocode, or an untested guess is not a concrete mapping for
`VERIFIED` status. Feature-documentation evidence is relayed through
`result_relay`; it does not add a tenth capability.

## Support states

| State | Meaning | Eligible for implementation writes |
| --- | --- | --- |
| `VERIFIED` | Every required operation is mapped and exercised on every claimed surface for the declared versions. An optional PLAN-task mapping is eligible only after its separate live read-only evidence gate. | Yes, for WORK after approval and capability revalidation. |
| `EXPERIMENTAL` | A candidate or runnable mapping exists but verification is incomplete or limited. | No. |
| `AUTHORING_ONLY` | A candidate mapping is documented without runnable support; no implementation support is claimed. | No. |
| `UNSUPPORTED` | One or more required operations have no acceptable host mapping. | No. |

Only `VERIFIED` adapters are eligible for WORK writes. User consent, a
populated contract, or conceptual similarity cannot change a support state or
bypass this gate. Promotion requires retained verification evidence and a
deliberate adapter release.

## Selection and validation

The Planner performs this read-only gate before requesting implementation
approval, writing an approved contract, or allowing WORK writes:

1. Call the candidate mapping's `identify_host` logic using host-provided
   signals.
2. Collect adapter references whose `host_id` exactly matches the identified
   host and whose claimed surface contains the active surface.
3. Require exactly one matching adapter with `support_state: VERIFIED`.
4. Require exact Core compatibility for `protocol_version` and the exact
   `adapter_version`; older metadata is incompatible, not a routing fallback.
5. Require all nine capability ids exactly once and confirm every operation's
   host mechanism is available in the current task.
6. Validate the WORK model and effort through the adapter. For an optional PLAN
   dispatch, validate every explicit per-task model override as well.
7. Record host, adapter, versions, routing, authorization, and policy in the
   proposal and approved contract.
8. Repeat capability, support-state, model, and version validation immediately
   before dispatch.

Protocol `0.7` has no implicit compatibility range. Workflow `0.7.1` uses
schema `2.1` and configuration revision `3`. Approved `0.7.0` and `0.6.x`
contracts remain immutable and continue only with their matching historical
Skill, Core, adapter, schema, and configuration resources. They are not
paired with `0.7` metadata implicitly. A same-version adapter without the
optional PLAN-task capability remains WORK-eligible and forces direct PLAN
handling.

Selection is per task. Never merge two partial adapters, select an adapter by
filename alone, promote an artifact through consent, or fall back to an
ineligible state.

## Failure behavior

Return `CAPABILITY_UNAVAILABLE` and stop before approval or writes when:

- the host or active surface cannot be identified;
- no adapter matches or multiple verified adapters match;
- the only matching adapter is not `VERIFIED`;
- protocol or adapter metadata is missing or incompatible;
- any required capability or host mechanism is unavailable; or
- model validation or dispatch cannot be represented faithfully.

An adapter without the optional PLAN-task capability uses direct PLAN handling;
it must not silently claim or bypass the missing mapping. The capability report
names the host, candidate adapters, failed operation, and observed evidence.

After approved WORK has started, use the Core result states: `BLOCKED` for a
user decision, authority, permission, documentation obligation, or contract
revision; `FAILED` for an evidence-backed environmental or execution failure
that cannot progress under the same conditions.

## Verification and promotion

Before setting `support_state: VERIFIED`, exercise all required operations on
each claimed surface and retain evidence for:

- positive host identification and rejection on a different host;
- Planner identity and user-facing ownership;
- valid, invalid, and explicit-inheritance model selections;
- exactly one WORK worker with the full envelope, including coding-rule paths;
- sandbox and approval-policy preservation;
- interruption, continuation, completion, and safe replacement;
- progress observation without a second writer;
- lossless relay of all three Core result schemas and their `DOCUMENTATION`
  evidence;
- non-mutating handling for `version_control_system: none` and read-only Git
  baseline inspection;
- rejection of staging, commit, and push when exact authorities are absent;
- exact-path staging, staged-diff inspection, compliant commit, clean
  post-commit state, and separately authorized push handling in an isolated
  Git fixture; and
- capability-unavailable behavior before writes for every non-`VERIFIED` state.

For an adapter declaring `read_only_scout_dispatch`, promotion additionally
requires a live PLAN micro-task test with Luna/max that confirms exact task
isolation, model override, policy enforcement, Evidence Packet relay with the
enums, fact fields, external-source records, and research result above, and
unchanged pre/post source worktree state.
For Codex, the recorded 2026-09-03 micro-task evidence satisfies this gate for
the tested task path, so its optional mapping is declared. Other adapters, or
broader untested paths, remain unclaimed until they retain equivalent evidence;
direct PLAN fallback still applies whenever the verified mechanism is absent
or policy limits are exceeded.
