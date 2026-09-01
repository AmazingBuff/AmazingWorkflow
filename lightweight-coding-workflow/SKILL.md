---
name: lightweight-coding-workflow
description: Orchestrate requested code changes as user-facing planning in the current main task followed by implementation by one worker using a user-approved model and a verified host adapter. Use when a user asks to build, change, refactor, or fix code and the work should require requirement confirmation, plan approval, explicit implementation-model selection, and strict separation between planning and code writes. Do not use for read-only explanation, review, or diagnosis unless implementation is also requested.
---

# Lightweight Coding Workflow

Workflow revision: `0.6.2`.

Protocol version: `0.6`.

Keep the current main task as the only user-facing Planner. Delegate approved product-code writes to one implementation worker using a user-approved model and a verified host adapter. Route Phase 1 repository discovery through the Context Routing reference: direct inspection for small tasks, or read-only scout subagents on a cheap, explicitly authorized model for large or multi-boundary tasks.

## Required resources and adapter gate

Before requesting approval, creating an approved contract, dispatching implementation, or interpreting a result, load the resources required by the current lane and Documentation Impact:

1. Read [references/protocol.md](references/protocol.md) completely.
2. Read [references/adapter-contract.md](references/adapter-contract.md) completely.
3. Identify the current host using read-only host signals, find the one matching adapter reference, and read that adapter completely.
4. Load [references/context-routing.md](references/context-routing.md) and `assets/context-routing/default-config.yaml` before making the routing decision. Load [references/orchestration-contracts.md](references/orchestration-contracts.md), the plan/Evidence Packet schemas, and the routing scripts only if the orchestrated lane is selected.
5. Determine whether the workspace is Git-backed using read-only inspection. For Git repositories, load [references/git-commit-convention.md](references/git-commit-convention.md) before the Git portion of the proposal.
6. Load the canonical [Feature Documentation Convention](references/feature-documentation-convention.md) before classifying Documentation Impact; load [assets/feature-document.md](assets/feature-document.md) only when the decision is `create`.
7. Require exactly one matching adapter with `support_state: VERIFIED`, exact protocol and adapter-version compatibility, all nine required capabilities, and concrete mappings for every required operation.
8. Use only that adapter's `identify_host`, `bind_planner`, `validate_model`, `dispatch_worker`, `inherit_permissions`, `control_lifecycle`, `report_progress`, `relay_result`, and `manage_version_control` operations. Use `read_only_scout_dispatch` only when the selected adapter explicitly declares and verifies that optional capability.

Fast-lane startup does not require orchestration-only, Git-only, documentation-only, or adapter-authoring references before those decisions are relevant. Progressive loading never waives a later gate.

Before approval or dispatch, the contract's `workflow_revision`, `protocol_version`, `protocol_sha256`, `host_adapter`, `adapter_version`, and `adapter_sha256` must be populated from the exact loaded source files. The selected adapter verifies these values before any implementation worker starts.

Workflow revision compatibility is explicit: contracts approved under workflow revision `0.6` remain immutable and use their matching historical resources. New `0.6.2` contracts require the evidence fields above; this release does not change Core protocol `0.6` or Codex Adapter `0.6`.

Workflow revision `0.6.2` migrates text-resource digests from the prior `0.6.1` raw-byte semantics to one canonical UTF-8/LF representation: decode UTF-8 text, normalize CRLF and lone CR to LF, re-encode as UTF-8, and hash it with SHA-256. This applies to configuration, protocol, and adapter text; binary and generated packet artifacts retain raw-byte hashing because their byte identity matters. Existing approved `0.6.1` contracts may continue with matching historical `0.6.1` resources; reapproval is required only to run a task under workflow revision `0.6.2` and its canonical UTF-8/LF text-digest semantics.

Complete this gate before asking the user to approve implementation or performing any product-code write. `EXPERIMENTAL`, `AUTHORING_ONLY`, and `UNSUPPORTED` adapters are not eligible for implementation. User consent cannot promote an adapter or authorize it to cross the write gate. If no adapter matches, more than one verified adapter matches, or any required capability is unavailable, return `CAPABILITY_UNAVAILABLE` with the host, adapter candidates, and missing capability; do not approve a contract, dispatch a worker, or implement in the Planner as a fallback.

Create contracts from [assets/implementation-contract.md](assets/implementation-contract.md). Create canonical feature documents from [assets/feature-document.md](assets/feature-document.md) when the approved Documentation Impact is `create`. Do not invent another contract or result schema.

## Core invariants

- The current main-task model is the Planner. Never replace it with a planning worker or override it.
- Only the Planner communicates with the user.
- The workflow has exactly two phases: planning and implementation. Scouting is a read-only Phase 1 activity, not a third phase.
- Scout subagents return evidence packets with locators; they never write product code, change requirements, or make routing or contract decisions.
- No Scout dispatch occurs before the Planner records explicit discovery authorization with the exact scout model, packet count, and token ceiling.
- Only one implementation worker may own writes to a worktree at a time.
- The Planner does not modify product code; the implementation worker does not change approved requirements, architecture, dependencies, public behavior, or scope.
- Product-code writes require both an approved contract and a user-approved implementation-model choice.
- The model choice is explicit for every dispatched role. Never silently substitute another model or reasoning effort.
- The approved contract is immutable. A material change requires a new approved revision.
- Permissions remain bounded by the current host task. An adapter must not broaden authorization.
- Verification belongs to the implementation worker. The Planner may perform only read-only confirmation after the worker returns.
- Required feature documentation is implementation material, not a third phase, and cannot substitute for readable code or verified tests.

## Phase 1: Plan

### Understand the request

1. Separate the request into objective, required behavior, constraints, non-goals, and acceptance criteria.
2. Make the routing decision from the Context Routing reference and the effective default configuration: estimate the discovery surface (files, tokens, and information boundaries), then choose the fast lane (direct inspection) or the orchestrated lane (scout subagents). Record the decision and its basis.
3. For the orchestrated lane, prepare and validate a plan with explicit discovery authorization. Only after that authorization passes may a verified optional Scout adapter capability dispatch read-only scouts; merge their validated Evidence Packets. Otherwise inspect directly in the fast lane.
4. Inspect relevant repository instructions, code, tests, version state, and uncommitted changes with read-only tools, using only the references required by the selected lane and impact.
5. Reuse facts already supplied by the user or repository.
6. Ask only about decisions that materially affect behavior, architecture, compatibility, dependencies, data, destructive operations, or scope.
7. State low-risk, reversible assumptions explicitly.

Keep planning in the main task. Do not create a separate planning worker. A scout is not a planning worker: it produces evidence only.

### Prepare the proposal

Present:

- objective and non-goals;
- numbered requirements;
- implementation approach and expected paths;
- the routing decision and its basis, and for the orchestrated lane the scout model and estimated token spend;
- for the orchestrated lane, explicit discovery authorization containing the exact scout model, packet count, and token ceiling;
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
3. Create the contract from the bundled asset, populate `workflow_revision`, `protocol_version`, `protocol_sha256`, `host_adapter`, `adapter_version`, and `adapter_sha256` from the exact loaded Skill/Core/adapter files, and populate every other field, including the complete Version control section, applicable coding-rule paths, and Documentation section.
4. Verify the populated revision and SHA-256 fields against those exact files, then set `status` to `APPROVED` and preserve the approved contract unchanged.

Creating task records does not authorize product-code edits, changes to repository ignore rules, staging, commits, or pushes.

## Phase 2: Implement

### Dispatch through the selected adapter

1. Confirm that no other write-capable worker owns the worktree.
2. Revalidate the adapter metadata, all nine required capabilities, and the approved contract's workflow/protocol/adapter revision and SHA-256 fields immediately before dispatch.
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

The Planner's final report states the outcome, implementation model, host adapter and version, routing decision and scout model (when the orchestrated lane ran), changed files, acceptance and command evidence, Documentation Impact and evidence, version-control system and baseline, Changelog disposition, commit status or proposed message, push status, unverified items, risks, and contract path and revision.

Do not stage, commit, push, deploy, publish, delete user work, or perform another external write unless the approved contract explicitly authorizes the exact action. Commit authority never implies push authority.

## Source, installation, and parity

The repository package is the source of truth. The current Codex layout separates the Skill and custom Agents:

- resolve the Codex root as `Path(os.environ["CODEX_HOME"])` when `CODEX_HOME` is set and non-empty, otherwise use `Path.home() / ".codex"`;
- copy the package files from `lightweight-coding-workflow/` (excluding `agents/*.toml`) to `<Codex root> / "skills" / "lightweight-coding-workflow"`;
- copy `agents/lightweight_implementer.toml` and `agents/lightweight_scout.toml` to `<Codex root> / "agents"`;
- keep the model-neutral Agent files free of model and permission overrides that would defeat per-task validation or the read-only Scout sandbox.

Installation is a separate, explicitly authorized action. Before and after a copy, run the read-only `scripts/check_install_parity.py` with explicit source and install paths. It compares package file hashes, package-owned Agent hashes, and Skill protocol versions; exit `0` means parity and exit `1` reports drift. The checker never writes, deletes, or overwrites either location, and unrelated custom Agents are outside its comparison set.
