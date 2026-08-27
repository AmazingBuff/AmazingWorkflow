# Context Routing

Contract version: `0.6` (part of the Core protocol at the same version).

This reference integrates context-efficient orchestration into Phase 1 planning. It defines when the Planner delegates read-only discovery to scout subagents, how sources are routed by information boundary, how the approved contract inherits precise locators so the implementation worker does not re-discover them, and which model each role runs on. The orchestration layer is scaffolding for planning; the approved contract remains the sole implementation authority.

The scout orchestration field contracts (source descriptor, shared fact, plan, task packet, expansion request, evidence packet) live in [orchestration-contracts.md](orchestration-contracts.md). This reference defines when and why they are used; that reference defines their exact shape.

## Core invariants

- Scouting belongs to Phase 1. It never writes product code, never changes requirements, and never replaces Planner judgment.
- A scout is not a planning worker. It returns evidence packets with locators; the Planner remains the only decision-maker and the only agent talking to the user.
- No scout is dispatched before the routing decision is made, and no scout runs after the contract is approved except optional read-only verification collection.
- The orchestration plan is disposable scaffolding. Only its evidence locators and confirmed facts survive into the contract.
- Scout model selection is explicit and user-visible, exactly like implementation-model selection. It defaults to a cheaper model but the user can override it.
- All scout reads respect the same read-only discipline as Planner inspection.

## Model routing policy

Each role has a cost tier. The Planner assigns tiers when preparing the routing decision and records the scout model in the proposal.

| Role | Default tier | Responsibility |
| --- | --- | --- |
| Planner (main task) | Expensive, user's current model | Requirement decomposition, routing decision, contract authoring, conflict adjudication, final report. |
| Scout subagent | Cheap, explicit user-approved model | Inventory, locate, materialize assigned selectors, produce evidence packets. |
| Implementation worker | User-approved implementation model | Product-code writes under the approved contract. |

Rules:

- The Planner never offloads contract authoring or approval decisions to a scout.
- The scout model must be validated through the host adapter before dispatch, using the same validation rules as the implementation model. If the host cannot represent a cheaper scout model, the Planner falls back to direct inspection and says so in the proposal.
- A cheap model that repeatedly produces weak evidence packets is a routing failure, not a contract problem; return to the routing decision rather than expanding the scout's scope.

## Routing decision and the small-task fast lane

The Planner makes one routing decision at the start of Phase 1, after understanding the request but before repository inspection:

1. **Fast lane** (direct inspection): the Planner reads the repository itself with read-only tools. No orchestration plan, no scouts, no packets.
2. **Orchestrated lane**: build an orchestration plan, validate it, generate scout task packets, dispatch read-only scouts, merge evidence packets.

Enter the orchestrated lane only when at least one condition holds:

- Estimated discovery surface exceeds **5 files** or **8,000 estimated tokens**.
- The task spans multiple modules or subsystems with distinct information boundaries.
- Independent verification of specific claims is worth deliberate duplicate reading.
- A single context would mix unrelated evidence and degrade planning quality.

Otherwise use the fast lane. These thresholds are starting points: tune them from measured runs and record adjusted values in project configuration. When in doubt, prefer the fast lane; orchestration overhead on a small task exceeds what it saves.

The routing decision, its basis, and (for the orchestrated lane) the scout model and token estimate are presented in the proposal so the user sees the cost shape before approving implementation.

## Orchestrated lane workflow

### 1. Inventory before reading

Use directory listings, symbol indexes, headings, manifests, and metadata first. The Planner does not bulk-read sources merely to decide who should read them. Follow the source-descriptor rules in [orchestration-contracts.md](orchestration-contracts.md): stable IDs, narrow selectors (symbol > line range > small file > whole file), estimated token counts.

### 2. Decompose by information boundary

Split scout tasks around the smallest evidence set that supports a planning conclusion: module, subsystem, claim, or failure-mode boundaries. Each task gets one objective, assigned source IDs, required questions, `deny`-or-`request` expansion (scouts may not self-expand), and stop conditions.

### 3. Validate and build packets

```bash
python scripts/validate_plan.py path/to/plan.json
python scripts/build_task_packets.py path/to/plan.json --out path/to/packets
```

Store both under the task-record directory (for example `.codex/task-runs/<task-id>/`). Fix validation errors; treat overlap warnings as prompts to narrow scope.

### 4. Dispatch scouts

Dispatch through the host adapter's `read_only_scout_dispatch` capability when the adapter provides one (protocol `0.6`). Without that capability the orchestrated lane degrades to direct inspection: the Planner materializes each packet's assigned selectors itself and keeps the evidence in its own context. Never bypass the adapter to spawn scouts.

Give each scout: the task packet, materialized source fragments (or instructions to read exactly the assigned selectors when the host enforces read-only subagents), the result-packet contract, and the scout model selection.

### 5. Merge evidence into planning

The Planner merges evidence packets by claim and locator, deduplicates facts, resolves conflicts by preferring direct evidence over summaries, and records remaining uncertainty. Conflicting material claims trigger at most one narrow re-read, not a full re-dispatch.

### 6. Hand locators to the contract

Requirements, allowed paths, and acceptance criteria in the contract should reference surviving locators (`path:symbol`, `path:lines a-b`) so the implementation worker starts from precise coordinates instead of re-discovering them. The contract's Discovery section records the routing decision, scout model, and measured token spend.

## Fast lane workflow

The Planner inspects directly with read-only tools, reads only what the routing decision identified as necessary, and records the inspected surface in the contract's Discovery section with `routing: direct`. No plan JSON or packets are created. If mid-planning the discovery surface grows past the thresholds, stop, make a fresh routing decision, and tell the user the cost shape changed.

## Instruction hierarchy

If the standalone `context-efficient-agent-orchestrator` skill (a general-purpose, non-coding orchestration skill distributed separately) is also loaded:

1. The two-phase Core invariants (single Planner, single writer, two phases, approval gates) always win.
2. This reference defines the coding-specific binding (routing decision, model tiers, fast lane, locator handoff).
3. The standalone skill's general rules apply only where neither this reference nor [orchestration-contracts.md](orchestration-contracts.md) covers the same ground; on any conflict the local contracts win for coding tasks.

The standalone skill is not a runtime dependency of this workflow: nothing here requires it to be installed. Its multi-writer or review-dispatch patterns are out of scope here: implementation-phase fan-out beyond the single approved worker is forbidden by the Core protocol.

## Fact routing rule (bound from [orchestration-contracts.md](orchestration-contracts.md))

A shared fact is delivered only to tasks whose assigned sources intersect the fact's provenance. Facts with empty provenance or `always_share: true` reach every task. Because facts that survive into the contract become requirement evidence, the Planner must check that every contract-relevant fact was actually delivered to the task that produced the supporting evidence, and mark contract-critical facts `always_share: true` when in doubt.

## Token estimation

Use `scripts/estimate_tokens.py` when a host tokenizer is unavailable. It counts CJK characters near one token each and other text near four characters per token. Estimates gate the routing decision and the budget; treat them as planning guidance, not billing truth.

## Output behavior

The orchestrated lane produces, under the task-record directory: `orchestration-plan.json`, scout packets, the packet manifest, and evidence packets as they return. The contract's Discovery section summarizes: routing decision and basis, scout model, estimated and measured token spend, and the evidence-locator index. When no scheduler executed the plan, the Discovery section must say `dispatched: no` and the proposal must not claim scouting occurred.
