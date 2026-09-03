# PLAN Context Routing

Contract version: `0.7` (part of the Core protocol at the same version).

This reference defines how the main Planner chooses direct handling, one
minimal micro Evidence Task, or a validated batch of independent read-only
Evidence Tasks. Routing is PLAN scaffolding; the approved implementation
contract remains the sole WORK authority.

The effective configuration is
`assets/context-routing/default-config.yaml`. A routing record copies its
revision and digest and records a resolved policy snapshot. The semantic
authority is `scripts/validate_plan.py`; the JSON schema and
`scripts/check_contract_parity.py` are checked mirrors. The full field shapes
are in [orchestration-contracts.md](orchestration-contracts.md).

## Two-phase and task-capability invariants

- The only public control phases are `PLAN` and `WORK`.
- Direct inspection and read-only task Agents are activities inside PLAN, not
  a third phase and not planning workers.
- The main Planner owns requirements, routing, user interaction, approval,
  contract authoring, conflict adjudication, and final reporting.
- PLAN task Agents return validated Evidence Packets. They do not decide
  scope, author or approve contracts, write files, mutate external systems,
  or spawn Agents.
- WORK retains exactly one user-approved implementation Agent for all writes,
  verification, and in-scope repair.

## Supported task kinds

The stable Agent id `lightweight_scout` is the task-scoped read-only Evidence
Task Agent. It accepts exactly:

- `requirement-research`
- `repository-read`
- `dependency-check`
- `evidence-analysis`

The `implementation` task kind belongs only to WORK and is rejected by PLAN
and Evidence Packet validators. Every PLAN task declares one kind, one
objective, exact source descriptors or query, a budget, stop conditions, and
the Evidence Packet response contract.

## Context-economics routing

The routing decision is not gated by a minimum file count or token count. The
Planner estimates:

- `planner_context_savings`: context removed from the main Planner;
- `delegated_input_tokens`: task input, including the assigned source estimate;
- `estimated_result_tokens`: compact evidence returned to the Planner;
- `coordination_overhead_tokens`: packet, dispatch, and merge overhead;
- `weighted_cost_savings`: an estimated model-weighted cost delta; and
- `weighted_cost_rationale`: why the estimate is credible and that total-token
  savings are not being claimed.

Delegation is beneficial when the task is independently describable and either
Planner-context savings exceed coordination overhead or weighted-cost savings
are positive. This is a planning estimate, not a billing measurement. A
subagent can increase total tokens while reducing the Planner's context load.
Never report total-token savings without measured evidence.

Use the following decision policy:

1. `direct` when evidence is already present, the evidence is tiny, or the
   work requires continuous Planner judgment; direct is also the safe fallback
   when the economics are not positive.
2. `micro` when exactly one bounded evidence task clears the economics gate,
   even when it covers one file or one question. A micro envelope is standalone
   and does not require a full orchestration plan.
3. `batch` when multiple independent tasks, distinct information boundaries,
   or deliberate duplicate review clear the economics gate. Batch uses the
   full plan, source routing, dependency layers, packets, and Evidence Packet
   merge.

The executable `choose_routing` helper in `scripts/validate_plan.py` applies
this policy. A direct choice may be recorded even when delegation would be
economically positive; the validator reports that as a review warning rather
than forcing delegation.

## Pre-authorized Codex PLAN-task policy

Codex's in-policy PLAN task defaults are:

- `gpt-5.6-luna` with reasoning effort `max`;
- at most two concurrent read-only tasks;
- at most 12,000 estimated input tokens per PLAN round;
- no complete parent transcript;
- host-enforced read-only sandbox, no writes, and no external mutations;
- one user-visible dispatch notice; and
- no per-task approval while the policy is not exceeded.

Exceeding a limit requires explicit user approval or direct PLAN fallback. The
adapter validates the exact model and reasoning effort; the host-neutral
configuration does not authorize a model substitution.

## Routing records

### Direct

A direct `routing-decision` record contains the goal and economics only. It
does not contain task packets, source bytes, or a full orchestration plan.

### Micro

A micro envelope contains one task id and supported task kind, one exact query,
one or more source descriptors, objective, deliverable, stop conditions,
allowed expansion, input/result budgets, economics, policy and authorization
snapshots, read-only execution rules, and the Evidence Packet response
contract. It never carries the complete parent transcript.

Validate a micro envelope with:

```bash
python scripts/validate_plan.py path/to/micro-task.json
python scripts/build_task_packets.py path/to/micro-task.json --out path/to/packets
```

The builder emits one packet and a manifest; it does not create a batch plan.

### Batch

A batch plan records source descriptors, shared facts, task kinds, dependencies,
expansion policy, budgets, economics, authorization, and merge checks. The
Planner validates and builds packets before any optional adapter dispatch:

```bash
python scripts/validate_plan.py path/to/batch-plan.json
python scripts/build_task_packets.py path/to/batch-plan.json --out path/to/packets
```

Dependency-free tasks may run concurrently, but no dispatch layer may exceed
two tasks under the Codex policy. The Planner materializes only assigned source
selectors after packet generation and replaces upstream placeholders with
compact dependency summaries. It never attaches the complete parent
transcript.

`--overwrite` may replace only packet files authenticated by a matching
generated manifest. Unrelated or unauthenticated files fail before deletion.

## Optional adapter dispatch and verification gate

An adapter may expose `read_only_scout_dispatch` as the historical metadata
name for task-scoped PLAN dispatch. It must enforce the task envelope, exact
selectors/query, policy limits, model selection, read-only permissions, and
Evidence Packet relay. An adapter without the optional capability uses direct
PLAN handling; it must not bypass the adapter to spawn a task.

The Codex reference contains a mapping promoted by the parent Planner's live
`gpt-5.6-luna/max` forward test. That evidence proves task isolation, explicit
model selection, lossless Evidence Packet relay, and identical pre/post source
worktree state for one micro repository-read task. Documentation alone is not
evidence; expansion, batch scheduling, and other host surfaces retain their
own verification boundaries. Direct handling remains the fallback when the
verified mechanism is unavailable or policy limits are exceeded.

## Evidence and compatibility

Evidence Packets use schema `2.0` and
`scripts/validate_evidence_packet.py`. Every material finding cites a source
id and precise locator. The response contract specifies finding severity
`low|medium|high|critical`, finding confidence `low|medium|high`, fact fields
`id|statement|provenance|confidence`, and fact confidence
`confirmed|inferred|unverified`. Expansion requests are proposals; only
Planner-approved requests may appear in `expansions_used`, and `deny` tasks
cannot expand.

Workflow `0.7.0` and Protocol `0.7` use schema/config revision `2.0`/`2`.
Approved `0.6.x` contracts are immutable and continue only with their matching
historical resources; they are not silently migrated by this reference.
