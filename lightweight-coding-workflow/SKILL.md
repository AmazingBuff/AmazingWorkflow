---
name: lightweight-coding-workflow
description: Orchestrate requested code changes as user-facing planning in the current main task followed by implementation by one worker using a user-approved model and a verified host adapter. Use when a user asks to build, change, refactor, or fix code and the work should require requirement confirmation, plan approval, explicit implementation-model selection, and strict separation between planning and code writes. Do not use for read-only explanation, review, or diagnosis unless implementation is also requested.
---

# Lightweight Coding Workflow

Protocol version: `0.5`.

Keep the current main task as the only user-facing Planner. Delegate approved product-code writes to one implementation worker through exactly one `VERIFIED` host adapter.

## Required resources and adapter gate

Before requesting approval, creating an approved contract, dispatching implementation, or interpreting a result:

1. Read [references/protocol.md](references/protocol.md) completely.
2. Read [references/adapter-contract.md](references/adapter-contract.md) completely.
3. Read the canonical [Feature Documentation Convention](references/feature-documentation-convention.md) completely before classifying Documentation Impact or preparing the proposal.
4. Determine whether the workspace is Git-backed using read-only inspection. For Git repositories, read [references/git-commit-convention.md](references/git-commit-convention.md) completely before preparing the proposal.
5. Identify the current host using read-only host signals.
6. Find the adapter reference under `references/adapters/` whose `host_id` matches that host.
7. Require exactly one matching adapter with `support_state: VERIFIED` and read it completely.
8. Validate that its `protocol_version` is compatible, its `adapter_version` is present, and every required capability and operation from the Host Adapter Contract has a concrete mapping.
9. Use only that adapter's `identify_host`, `bind_planner`, `validate_model`, `dispatch_worker`, `inherit_permissions`, `control_lifecycle`, `report_progress`, `relay_result`, and `manage_version_control` operations.

Complete this gate before asking the user to approve implementation or performing any product-code write. `EXPERIMENTAL`, `AUTHORING_ONLY`, and `UNSUPPORTED` adapters are not eligible for implementation. User consent cannot promote an adapter or authorize it to cross the write gate. If no adapter matches, more than one verified adapter matches, or any required capability is unavailable, return `CAPABILITY_UNAVAILABLE` with the host, adapter candidates, and missing capability; do not approve a contract, dispatch a worker, or implement in the Planner as a fallback.

Create contracts from [assets/implementation-contract.md](assets/implementation-contract.md). Create canonical feature documents from [assets/feature-document.md](assets/feature-document.md) when the approved Documentation Impact is `create`. Do not invent another contract or result schema.

## Core invariants

- The current main-task model is the Planner. Never replace it with a planning worker or override it.
- Only the Planner communicates with the user.
- The workflow has exactly two phases: planning and implementation.
- Only one implementation worker may own writes to a worktree at a time.
- The Planner does not modify product code; the implementation worker does not change approved requirements, architecture, dependencies, public behavior, or scope.
- Product-code writes require both an approved contract and a user-approved implementation-model choice.
- The model choice is explicit. Never silently substitute another model or reasoning effort.
- The approved contract is immutable. A material change requires a new approved revision.
- Permissions remain bounded by the current host task. An adapter must not broaden authorization.
- Verification belongs to the implementation worker. The Planner may perform only read-only confirmation after the worker returns.
- Required feature documentation is implementation material, not a third phase, and cannot substitute for readable code or verified tests.

## Phase 1: Plan

### Understand the request

1. Separate the request into objective, required behavior, constraints, non-goals, and acceptance criteria.
2. Inspect relevant repository instructions, code, tests, version state, and uncommitted changes with read-only tools.
3. Reuse facts already supplied by the user or repository.
4. Ask only about decisions that materially affect behavior, architecture, compatibility, dependencies, data, destructive operations, or scope.
5. State low-risk, reversible assumptions explicitly.

Keep planning in the main task. Do not create a separate planning worker.

### Prepare the proposal

Present:

- objective and non-goals;
- numbered requirements;
- implementation approach and expected paths;
- constraints and protected existing changes;
- the applicable bundled coding-rule components the worker must load before editing, or `None`;
- numbered acceptance criteria;
- real verification commands or explicit manual checks;
- Documentation Impact as `create`, `update`, or `not-required` with the canonical policy reason;
- for `create` or `update`, the canonical feature-document path, feature-index path, code and test entry points, required sections, and validation plan; for `not-required`, the specific stable reason and applicable verification entry points;
- risks and assumptions;
- the selected verified host adapter and its version;
- the exact implementation model and optional reasoning effort.

For a Git repository, also present one complete version-control plan:

- the repository root, branch or detached state, baseline revision, current index/staged state, and uncommitted paths to preserve;
- the single logical commit boundary and exact paths it would contain, including required feature documentation and index updates;
- whether a Changelog entry is required and, when required, its file, category, and proposed user-facing entry;
- the proposed Conventional Commit message;
- commit authority and push authority as separate decisions, including an exact remote and refspec if push is proposed.

Default both authorities to `none`. Approval of implementation, the contract, a model, or an adapter never grants staging, commit, or push authority implicitly. For a non-Git workspace, record `version_control_system: none` and do not propose Git operations.

Use the selected adapter's model-validation rules. A model, project default, parent inheritance, or reasoning effort is valid only when the user explicitly approves the value as the adapter defines. If the adapter cannot represent or validate the selection, follow its failure mapping; never invent a fallback.

### Approval gate and contract

Obtain explicit approval of the complete proposal, adapter, and implementation-model choice. General enthusiasm, silence, or approval of a materially different revision is insufficient.

After approval:

1. Capture the repository root, branch or detached state, revision, index/staged state, uncommitted paths, and changes that must be preserved.
2. Use the selected adapter's Planner binding to resolve the task-record location.
3. Create the contract from the bundled asset, confirm its fixed `protocol_version` matches the loaded Core, and populate every placeholder, including `host_adapter`, `adapter_version`, the complete Version control section, the applicable coding-rule paths, and the Documentation section with its decision, paths, entry points, required sections, and validation obligations.
4. Set `status` to `APPROVED` and preserve the approved contract unchanged.

Creating task records does not authorize product-code edits, changes to repository ignore rules, staging, commits, or pushes.

## Phase 2: Implement

### Dispatch through the selected adapter

1. Confirm that no other write-capable worker owns the worktree.
2. Revalidate the adapter metadata and all nine required capabilities immediately before dispatch.
3. Validate the approved model and optional reasoning effort through the adapter.
4. Dispatch exactly one worker through the adapter, passing the absolute approved-contract path, the absolute path to the loaded Core protocol, task id, revision, the exact adapter-defined model selection, and the absolute paths of the coding-rule components listed by the contract.
5. Tell the worker to treat the contract as the sole authority, avoid user questions and scope expansion, spawn no other writer, and return exactly one Core result schema.

Do not dispatch an additional writer, reviewer, tester, or explorer. If dispatch or capability validation fails, use the adapter's failure behavior and do not implement in the Planner.

### While implementation runs

- Use the adapter's lifecycle and progress operations.
- Keep raw implementation output with the worker and provide only concise user-facing progress when useful.
- Do not change requirements without stopping implementation and returning to planning.
- If the user changes material scope, stop or interrupt through the adapter, revise the contract, obtain approval, and continue the same worker when the adapter supports it.
- A replacement worker is allowed only after the previous writer is confirmed stopped, completed, or closed.

### Handle the result

Use the adapter's result-relay operation and the exact schemas in the Core protocol.

For `DONE`, inspect all acceptance evidence, command results, `DOCUMENTATION` evidence, Changelog disposition, commit status or proposed message, and push status. Confirm that required documents and index entries are current and navigable. The Planner may run read-only checks. If an approved item is unmet but repair remains in scope, continue the same worker through the adapter.

For `BLOCKED`, stop new implementation work, explain the decision to the user, and revise and reapprove the contract when behavior, scope, architecture, dependencies, allowed paths, destructive authority, acceptance criteria, or Documentation Impact changes.

For `FAILED`, report the evidence and worktree state. The Planner must not take over product-code writes.

## Completion

The Planner's final report states the outcome, implementation model, host adapter and version, changed files, acceptance and command evidence, Documentation Impact and evidence, version-control system and baseline, Changelog disposition, commit status or proposed message, push status, unverified items, risks, and contract path and revision.

Do not stage, commit, push, deploy, publish, delete user work, or perform another external write unless the approved contract explicitly authorizes the exact action. Commit authority never implies push authority.
