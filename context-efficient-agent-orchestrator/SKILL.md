---
name: context-efficient-agent-orchestrator
description: Plan and run context-efficient main-agent/subagent workflows over codebases, documents, repositories, or other large file sets. Use when an agent must decide whether to delegate, split work by information boundary, create scoped subagent task packets, prevent unnecessary re-reading of files, control token and overlap budgets, support independent review when justified, collect evidence-backed results, resolve conflicts, or expose a framework-neutral orchestration plan for a custom agent scheduler. Do not use for a simple single-agent task with no meaningful delegation or file-context management.
---

# Context-Efficient Agent Orchestrator

## Objective

Coordinate a main agent and subagents without treating the parent's hidden context as shared memory. Transfer only explicit facts, constraints, source references, dependency outputs, and task boundaries. Optimize accidental duplication while preserving deliberate independent verification.

## Required operating model

Map the host environment to these abstract capabilities before planning:

- `inventory`: list files, sections, symbols, records, or other source units.
- `locate`: search or identify likely relevant source units without bulk-reading them.
- `materialize`: read a file range, symbol, section, object, or search result.
- `dispatch`: invoke a subagent with an explicit task packet.
- `collect`: receive a structured result packet.
- `persist`: optionally store reusable facts, summaries, hashes, or indexes.

Use the available tools that best implement each capability. If `dispatch` is unavailable, produce an integration-ready plan and task packets; never claim that subagents were executed.

Interactive coding-agent host: when the host offers a subagent-dispatch tool but no separate materialization layer, the main agent acts as its own scheduler. It reads the assigned selector ranges itself, embeds the fragments into each subagent prompt after the task instructions, and applies the result-packet contract to the subagent's reply. When the host provides a read-only explorer subagent type, prefer it for scout work so the read scope stays enforced by the host, not by prompt discipline alone.

For coding tasks specifically, prefer the integrated form of this skill bundled inside `lightweight-coding-workflow` (see its `references/context-routing.md`); it adds model routing, an approval-gated dispatch path, and a small-task fast lane. This standalone skill remains the general-purpose version for non-coding corpora.

## Workflow

### 0. Apply the delegation gate

Delegate only when at least one condition is true:

- Work can proceed in parallel across distinct information boundaries.
- A specialist capability materially improves quality.
- Independent review is worth deliberate duplicate reading.
- A single context would be too large or would mix unrelated evidence.

Keep the task single-agent when delegation overhead is likely greater than the saved context or elapsed work.

### 1. Resolve control settings

Apply configuration in this precedence order:

1. Explicit user or caller settings.
2. Project-level orchestration configuration.
3. Selected mode defaults.
4. The `balanced` defaults in `assets/default-config.yaml`.

Use one mode:

- `lean`: minimize token use; almost no overlapping reads.
- `balanced`: default; scoped reads with limited verification.
- `independent-review`: intentionally duplicate only the material under review.
- `high-assurance`: permit multiple independent readers and stronger conflict checks.

Read `references/configuration.md` when tuning budgets, modes, expansion, caching, or capability adapters.

### 2. Inventory before reading

Inspect names, metadata, symbol indexes, headings, manifests, dependency graphs, hashes, and rough token estimates first. Do not let the main agent read every source merely to decide who should read it.

Create source descriptors with stable IDs and narrow selectors. Prefer, in order:

1. Symbol, section, object, or semantic result.
2. Explicit line or page range.
3. Small complete file.
4. Large complete file only when cross-cutting context makes narrower selection unsafe.

A source descriptor must include an estimated token count. Record uncertainty when the estimate is approximate.

### 3. Decompose by information boundary

Split tasks around the smallest evidence set that can support a useful conclusion. Prefer module, subsystem, claim, dataset slice, document section, or failure mode boundaries over arbitrary role labels.

For each task, define:

- One objective with a testable completion condition.
- The initial source IDs it may read.
- Required questions and deliverable.
- Dependencies on other task results.
- Evidence and confidence requirements.
- A bounded expansion policy.
- Stop conditions.

Avoid multiple tasks reading the same source unless the overlap is explicitly marked as intentional.

### 4. Build explicit shared context

Share only compact, reusable state:

- Confirmed facts with provenance.
- Clearly labeled inferences or assumptions.
- Global constraints and definitions.
- Tiny common interfaces or schemas when every applicable task genuinely needs them. Set `inherit_shared_sources: false` for synthesis-only tasks that do not need shared raw sources.
- Summaries of completed dependencies that the downstream task actually uses.

Do not pass the full parent transcript, private reasoning, or broad file dumps. Do not treat a parent summary as primary evidence when the subagent must verify the original source.

### 5. Create the orchestration plan

Use the canonical contract in `references/contracts.md` and the machine schema in `assets/orchestration-plan.schema.json`.

The plan must contain:

- Goal, mode, assumptions, and budgets.
- Shared facts, constraints, and optional shared source IDs.
- Stable source descriptors.
- Per-task objectives, read scopes, dependencies, expansion policies, and evidence rules.
- Merge and conflict-resolution policy.

When local execution is available, validate the plan before dispatch:

```bash
python scripts/validate_plan.py path/to/plan.json
```

Fix validation errors. Treat overlap and whole-file warnings as prompts to reconsider scope, not as automatic failures.

### 6. Generate and dispatch task packets

Generate one packet per task:

```bash
python scripts/build_task_packets.py path/to/plan.json --out path/to/packets
```

A task packet is a capability-neutral contract. The host scheduler must materialize only the packet's assigned source descriptors and insert only required dependency summaries.

Order the prompt for cache friendliness without adding irrelevant content:

1. Stable subagent role and response contract.
2. Stable project definitions that are truly shared.
3. Compact shared facts and constraints.
4. Task-specific objective and questions.
5. Materialized source fragments.

Never forward the full main-agent conversation merely to improve cache reuse.

### 7. Enforce controlled expansion

Start each subagent with its assigned scope. Allow additional reads only according to the task's `allowed_expansion` policy:

- `deny`: complete or report blocked using the assigned sources only.
- `request`: return a structured expansion request for scheduler approval.
- `bounded`: read additional sources up to the stated token allowance and record every expansion.

An expansion request must state the missing information, requested selector, expected value, and estimated token cost. Prefer the narrowest source that can resolve the blocker.

### 8. Collect evidence-backed result packets

Require subagents to return conclusions, not hidden reasoning. Each result must separate:

- Findings and supporting evidence locators.
- Reusable facts for the parent.
- Assumptions and confidence.
- Unknowns or blockers.
- Expansion actually used.
- Optional measured token usage.

Reject unsupported material claims when evidence was required.

### 9. Merge and resolve conflicts

Merge by claim and evidence, not by averaging prose. Deduplicate repeated facts and preserve the strongest source locator.

When results conflict:

1. Check whether agents used different source versions or scopes.
2. Prefer direct evidence over summaries and confirmed facts over inference.
3. Request the smallest missing source or clarification.
4. Dispatch an independent reviewer only when the conflict is material.
5. Record the final decision and remaining uncertainty.

The main agent may read a narrow source fragment for final adjudication. It should not re-read all sources by default.

### 10. Persist reusable state

When supported, persist compact artifacts that reduce future work:

- File and symbol indexes.
- Source hashes and version identifiers.
- Confirmed facts with provenance and expiry conditions.
- Task-result summaries.
- Known dependency relationships.

Invalidate persisted facts when their source hash or version changes.

## Non-negotiable rules

- Treat each agent invocation as an independent context unless the host explicitly guarantees shared context.
- Optimize accidental overlap, not all overlap. Independent verification may justify duplicate reads.
- Never transfer private chain-of-thought. Transfer explicit facts, evidence, decisions, and unresolved questions.
- Never let cache strategy justify adding unrelated sources.
- Never assign a task without a completion condition and response contract.
- Never use an unbounded recursive delegation policy.
- Preserve source provenance through every summary and merge.
- State clearly whether a plan was only generated or was actually dispatched.

## Output behavior

When executing with a real scheduler, return a concise final synthesis plus plan metrics, unresolved conflicts, and any budget exceptions.

When producing an integration artifact, return or save:

1. `orchestration-plan.json`
2. One task packet per subagent
3. A packet manifest with dependency order and token estimates
4. The expected result-packet contract

Read `references/contracts.md` for exact fields. Read `references/examples.md` when a decomposition pattern is unclear. Read `references/rust-integration.md` only when integrating with a Rust scheduler.

## Bundled resources

- `assets/default-config.yaml`: copyable baseline policy.
- `assets/orchestration-plan.schema.json`: JSON Schema for scheduler integration.
- `assets/example-plan.json`: validated example plan.
- `scripts/validate_plan.py`: deterministic structural, dependency, budget, and overlap validation.
- `scripts/build_task_packets.py`: deterministic packet and manifest generation.
- `references/configuration.md`: modes, budgets, formulas, and adapter behavior.
- `references/contracts.md`: plan, task, result, and expansion contracts.
- `references/examples.md`: common decomposition patterns.
- `references/rust-integration.md`: Rust-friendly data structures and scheduler adapter pattern.
- `agents/openai.yaml`: display metadata for OpenAI-hosted skill listings; not used at runtime.
