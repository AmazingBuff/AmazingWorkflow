---
name: lightweight-coding-workflow
description: Keep coding work in a user-facing PLAN followed by one implementation WORK task, with bounded read-only PLAN task delegation when context economics justify it and explicit approval gates for product writes.
---

# Lightweight Coding Workflow

Workflow revision: `0.7.0`.

Protocol version: `0.7`.

The main task is the only user-facing Planner. Product-code writes belong to
one implementation worker under an approved contract. PLAN may use bounded
read-only Evidence Task Agents when doing so is worth the coordination cost;
WORK preserves one persistent implementation writer and its verification and
repair lifecycle.

## Two-phase control model

The only public control phases are `PLAN` and `WORK`:

1. `PLAN` owns requirement interpretation, repository discovery, routing,
   proposal synthesis, capability validation, approval, contract creation,
   and final reporting. Direct inspection and optional read-only task Agents
   are activities inside PLAN, not extra phases.
2. `WORK` owns exactly one approved implementation task Agent, all allowed
   writes, verification, and in-scope review repair before ownership is
   released.

Agents are assigned by task capability, not by phase. The main Planner remains
the only decision maker and the only agent that communicates with the user.

## Required resources and adapter gate

Before requesting approval, creating a contract, dispatching a worker, or
interpreting a result, load the resources required by the current lane and
Documentation Impact:

1. Read [references/protocol.md](references/protocol.md),
   [references/adapter-contract.md](references/adapter-contract.md), and the
   selected adapter reference completely.
2. Identify the current host from host-provided signals and require exactly
   one matching adapter with `support_state: VERIFIED`, exact Protocol and
   Adapter compatibility, all nine required capabilities, and concrete
   mappings for every required operation.
3. Load [references/context-routing.md](references/context-routing.md) and
   `assets/context-routing/default-config.yaml` before routing. Load
   [references/orchestration-contracts.md](references/orchestration-contracts.md),
   the PLAN schemas, and routing scripts when batch orchestration is selected.
4. Load the Git convention only for Git-backed work and the canonical
   documentation convention when Documentation Impact is `create` or `update`.
5. Use only the adapter's `identify_host`, `bind_planner`, `validate_model`,
   `dispatch_worker`, `inherit_permissions`, `control_lifecycle`,
   `report_progress`, `relay_result`, and `manage_version_control` operations.
   Use optional `read_only_scout_dispatch` only when the selected adapter
   explicitly declares it and the live verification gate has passed.

`EXPERIMENTAL`, `AUTHORING_ONLY`, and `UNSUPPORTED` adapters cannot dispatch
product writes. If the host, adapter, model, permission, or required
capability is unavailable, return the adapter's capability failure before any
write; never bypass the gate or silently substitute a model.

Before approval and dispatch, an approved `0.7.0` contract must contain the
exact loaded `workflow_revision`, Core `protocol_sha256`, adapter version and
`adapter_sha256` evidence. Text digests use canonical UTF-8 with LF line endings; binary and
generated packet artifacts retain raw-byte hashing.

## Task-capability model

The stable custom Agent id `lightweight_scout` is a task-scoped, read-only
Evidence Task Agent. It accepts only these PLAN task kinds:

- `requirement-research`
- `repository-read`
- `dependency-check`
- `evidence-analysis`

Each task receives one independently describable objective, exact source
selectors or query, a budget, stop conditions, and the Evidence Packet result
contract. It reads no unassigned source without a Planner-approved expansion
and never writes files, changes requirements or scope, authors or approves a
contract, talks to the user, or spawns another Agent. `implementation` is the
separate WORK task capability and is never a PLAN Evidence Task.

The Evidence Packet contract is explicit: finding severity is `low`, `medium`,
`high`, or `critical`; finding confidence is `low`, `medium`, or `high`; fact
fields are `id`, `statement`, `provenance`, and `confidence`; and fact
confidence is `confirmed`, `inferred`, or `unverified`.

## PLAN routing: direct, micro, or batch

PLAN records a context-economics decision in the routing envelope:

- `direct`: the evidence is already present or tiny, or continuous Planner
  judgment is required. No task packet is created.
- `micro`: one bounded, independently describable Evidence Task is worthwhile
  even if it covers one file or one question. It uses the minimal micro-task
  envelope and does not require a full orchestration plan.
- `batch`: multiple independent Evidence Tasks, distinct information
  boundaries, or deliberate duplicate review justify the full validated plan,
  task packets, dependency layers, and Evidence Packet merge.

The former file/token minimum gate is not the decision rule. Delegation is
allowed only when the task is bounded and the estimated Planner-context
savings exceed coordination overhead or the estimated weighted-cost savings
are positive. Direct handling remains preferred when its evidence or judgment
is already available. Every delegated decision records estimated
Planner-context savings, delegated input tokens, estimated result size,
coordination overhead, and a weighted-cost rationale.

Delegation can increase total tokens. These estimates target Planner-context
load and weighted cost; they never establish total-token savings. A plan must
not claim total-token savings without measured evidence.

## Pre-authorized Codex PLAN-task policy

Within one PLAN round, Codex may dispatch read-only task Agents under the
following pre-authorized policy, with one user-visible dispatch notice and no
per-task approval:

- model: `gpt-5.6-luna`; reasoning effort: `max`;
- maximum concurrent tasks: `2`;
- maximum estimated input: `12,000` tokens for the round;
- host-enforced sandbox: read-only; no writes or external mutations;
- no complete parent transcript;
- exceeding any limit requires user approval or direct PLAN fallback.

The adapter must validate the explicit per-task model and effort. An optional
Codex declares its read-only PLAN-task mapping after the recorded live forward
test confirmed task isolation, result relay, explicit model selection, and an
unchanged source worktree. The evidence covers the tested micro path; broader
expansion, batch, and surface claims still require their own evidence.

## WORK single-writer lifecycle

After complete proposal, model, capability, and contract approval, revalidate
the baseline and dispatch exactly one `lightweight_implementer` worker through
the selected adapter. It receives the absolute contract and Core protocol
paths, task id and revision, exact model selection, and every applicable
coding-rule path. It owns all allowed writes, tests, documentation updates,
and verification. Keep the same worker for an in-scope repair or review
follow-up. A replacement is allowed only after the earlier writer is
confirmed stopped, completed, or closed.

The Planner never writes product code. The worker never asks the user, changes
the contract, expands scope, creates another writer, or stages, commits,
pushes, deploys, publishes, deletes data, or performs external writes without
exact contract authority. Version-control and push authority are separate and
default to `none`.

## Planning and approval

Separate the request into objective, requirements, constraints, non-goals,
acceptance criteria, risks, and reversible assumptions. The proposal includes
the routing decision and economics, task policy, expected paths, applicable
coding rules, verification, Documentation Impact, adapter, exact
implementation model and effort, and the complete Git baseline and authority
plan when applicable.

Create contracts from
[assets/implementation-contract.md](assets/implementation-contract.md). The
approved contract is immutable. A material change to behavior, architecture,
dependencies, paths, authority, acceptance, documentation, routing, model,
adapter, or resource evidence requires a new approved revision.

For Documentation Impact `create` or `update`, update the canonical feature
document and index atomically with the implementation and tests, then validate
links, required sections, navigation, and freshness. Required documentation
is implementation material, not a third phase.

## Compatibility and installation

Workflow `0.7.0`, Core Protocol `0.7`, schema `2.0`, and the effective routing
configuration revision `2` are coordinated. Approved `0.6.x` contracts remain
immutable and must continue with their exact historical Skill, Core, adapter,
schema, and configuration resources; they are not silently reinterpreted by
the `0.7.0` resources. A same-version adapter without the optional PLAN-task
capability remains eligible for WORK and uses direct PLAN handling.

The repository package is the source of truth. Resolve the Codex root as
`Path(os.environ["CODEX_HOME"])` when `CODEX_HOME` is set and non-empty;
otherwise use `Path.home() / ".codex"`. Copy package files from
`lightweight-coding-workflow/` (excluding `agents/*.toml`) to
`<Codex root>/skills/lightweight-coding-workflow`, and copy
`agents/lightweight_implementer.toml` and `agents/lightweight_scout.toml` to
`<Codex root>/agents`. Installation is separate and requires explicit
authorization. Before and after installation, run the read-only parity
checker; it must report exit `0` for parity.
