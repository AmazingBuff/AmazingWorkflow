---
host_adapter: "zcode"
host_id: "zcode"
display_name: "ZCode Host Adapter"
protocol_version: "0.7"
adapter_version: "0.4"
support_state: "VERIFIED"
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
verified_on: "2026-09-04"
---

# ZCode Host Adapter

Implementation dispatch eligibility: **yes**, only after contract/model approval and immediate capability revalidation. The optional PLAN-task dispatch mapping is declared for the tested read-only `Explore`/custom-scout micro path; its verified scope and remaining limits are recorded below.

This adapter is a `VERIFIED` protocol `0.7` mapping. It implements the [Host Adapter Contract](../adapter-contract.md) for the [Core protocol](../protocol.md), carries feature-documentation evidence, and preserves the model-neutral custom Agents. The read-only PLAN-task capability is separately verified and is not implied by WORK dispatch.

This candidate does not declare `managed_web_research`. Documentation of a
browser or subagent is not capability proof; until a future live read-only
forward test and adapter revision exist, the PLAN gate records managed search
as unavailable and uses direct Planner search, an explicit uncertain fallback,
or `BLOCKED`.

## Why this adapter exists

ZCode's built-in Agent tool offers a general-purpose subagent type and an `Explore` subagent type that is read-only by design. The `Explore` type maps naturally onto the optional `read_only_scout_dispatch` capability, because the host itself enforces the read-only scope rather than relying on prompt discipline.

ZCode binds a subagent's model at the definition level, not at dispatch time. User-scope agent definitions under `~/.zcode/agents/<name>.md` carry a `model` frontmatter field (a specific model, `inherit`, or empty), and even the built-in agents can carry a separately configured model and thought level. This per-definition binding is how the adapter represents the Core's explicit, user-approved model selection: choosing the approved model means dispatching the agent type whose definition binds it.

## Compatibility

| Item | Mapping |
| --- | --- |
| Core protocol | Exact version `0.7` |
| Adapter | `zcode` version `0.4` |
| Planner | Current ZCode main task and its selected model |
| Worker | One Agent-tool subagent of the agent type that binds the approved model: the custom `lightweight_implementer` definition for an exact model, or an unbound/`inherit` type for approved parent inheritance |
| Worker source | [lightweight_implementer.toml](../../agents/lightweight_implementer.toml) (Codex layout; ZCode uses the installed Markdown equivalent under `~/.zcode/agents/lightweight_implementer.md`) |
| PLAN task | Verified task-scoped read-only mapping via the `Explore` built-in type or a custom read-only scout definition binding the approved PLAN model; direct PLAN handling remains the fallback for unsupported or over-policy cases |
| Model binding | Per agent definition (`model` and optional `thoughtLevel` fields in `~/.zcode/agents/<name>.md`); the Agent tool exposes no per-dispatch model override |
| Agent definitions | `~/.zcode/agents/<name>.md`, Markdown body as the system prompt, user scope only in the current Beta; Codex-style `agents/*.toml` files from this package are not read by ZCode and need Markdown equivalents |
| Contract asset | Loaded Skill's `assets/implementation-contract.md` |
| Coding-rule components | Loaded Skill's `assets/coding-rules/**`, listed by absolute path in the contract |
| Task records | Repository-local `.zcode/task-runs/<task-id>/implementation-contract-v<revision>.md` |
| Result schemas | Core `DONE`, `BLOCKED`, and `FAILED` Markdown schemas with `DOCUMENTATION` evidence; PLAN tasks return Evidence Packets |

Protocol `0.7` requires exact adapter metadata. Older approved contracts remain immutable and continue only with matching historical resources or a newly approved revision.

Workflow revision compatibility: contracts approved under `0.6.x` remain immutable and use matching historical Skill, Core, adapter, schema, and configuration resources. New `0.7.0` contracts carry verified `workflow_revision`, `protocol_sha256`, and `adapter_sha256` evidence; the ZCode adapter version is `0.4`. Text-resource evidence uses the canonical UTF-8/LF digest representation documented by the Core; binary and generated packet artifacts retain raw-byte hashing.

## Operation map

| Capability | Operation | ZCode mechanism | Failure mapping |
| --- | --- | --- | --- |
| Host identification | `identify_host` | Confirm ZCode from host-provided session and tool metadata (ZCode harness markers in the system context, `mcp__node_repl` / ZCode plugin tool naming, session workspace paths) without writing. | `CAPABILITY_UNAVAILABLE` before approval if identity is absent or ambiguous. |
| Planner binding | `bind_planner` | Keep the current main task as the sole Planner; resolve resources from the loaded Skill and task records from the repository root. | `CAPABILITY_UNAVAILABLE` if the task, repository, or loaded resources cannot be resolved. |
| Model validation | `validate_model` | Validate the user-approved model against agent definitions loaded in the current session: an exact model requires a loaded definition binding exactly that model; `inherit-parent (user-approved)` requires a definition with `model: inherit` or no binding. | Return to planning; never substitute a model or effort. |
| Worker dispatch | `dispatch_worker` | One Agent-tool subagent of the model-bound agent type (`lightweight_implementer` for exact binding, or an `inherit` definition) with the complete Core WORK dispatch envelope as the subagent prompt. | `CAPABILITY_UNAVAILABLE` before writes if the agent type is not loaded or dispatch is unavailable. |
| Permission inheritance | `inherit_permissions` | Subagents inherit the session sandbox and permission mode; the host permission system mediates tool calls; the adapter omits permission-broadening configuration. | `BLOCKED` if an in-scope action needs unavailable approval or authority. |
| Lifecycle control | `control_lifecycle` | ZCode Agent-tool lifecycle: dispatch (foreground or `run_in_background`), notification on completion, `TaskOutput` to wait/observe, `TaskStop` to stop a running worker, and resume of a completed agent via its `agent_<uuid>` id for a follow-up; a replacement is permitted only after the earlier writer is confirmed stopped, completed, or closed. | `BLOCKED` for unresolved ownership; `FAILED` for unrecoverable host control failure. |
| Progress reporting | `report_progress` | Observe a background worker via `TaskOutput` (blocking or non-blocking) and completion notifications; relay only concise progress to the user while raw implementation output stays with the worker. | `FAILED` only when progress/result state cannot be recovered after evidence-based attempts. |
| Result relay | `relay_result` | The worker's final message returns to the main task as the Agent tool result; validate its status line and every required Core section, including `DOCUMENTATION`. | Continue the same worker for an in-scope malformed result; otherwise `FAILED`. |
| Version-control management | `manage_version_control` | Use read-only Git commands for baselines; use exact-path staging and commit only under exact contract authority; push only under separate remote/refspec authority. | `BLOCKED` for authority, overlap, or baseline conflicts; `FAILED` for an unrecoverable authorized Git operation. |
| PLAN task dispatch (optional) | `read_only_scout_dispatch` | One `Explore`-type subagent (or a custom read-only scout definition binding the approved PLAN model) per micro/batch task envelope, with exact source selectors/query, budget, stop conditions, and the Evidence Packet response contract; the host enforces read-only access; no complete parent transcript. | `CAPABILITY_UNAVAILABLE` when the host cannot provide the verified read-only mechanism or model; direct PLAN fallback when policy limits are exceeded. |

## `identify_host`

Preconditions: the workflow Skill is loaded in a ZCode task. Confirm host identity from host-provided session and tool metadata and confirm the active surface is `cli`. Do not infer ZCode solely from repository files or this adapter's presence.

Output: `host_id=zcode`, the active surface, and availability evidence for the Agent tool with custom agent types, permission inheritance, background task lifecycle, result return, and version-control management.

## `bind_planner`

Bind the current main task without spawning another planning agent. Its currently selected model remains the Planner model, and only this task communicates with the user.

Resolve:

- the repository root from the current task workspace;
- the Core, Adapter Contract, Git convention, feature-documentation convention, feature template, and coding-rule components from the loaded Skill location;
- the implementation-contract asset from the same loaded Skill;
- task records under `.zcode/task-runs/<task-id>/` in the repository.

Creating a task record does not authorize product-code writes or an ignore-file change.

## `validate_model`

ZCode resolves a subagent's model from its agent definition, not from the dispatch call. The effective model comes from the `model` frontmatter field of the dispatched agent's definition under `~/.zcode/agents/<name>.md` — a specific model id, `inherit`, or empty — while built-in agents (`general-purpose`, `Explore`) inherit the parent model unless a model is separately configured for that built-in. An unset model follows the main session's model, including after a mid-session model switch.

The Agent tool exposes no per-dispatch model parameter, so an approved model selection is representable only as an agent type that binds it. Validation therefore:

1. For an exact user-approved model, confirm that an agent definition loaded in the current session binds exactly that model, then dispatch that agent type. If no loaded definition binds it, return to planning with the set of representable models; creating a new binding definition is a planning-time proposal, and because agent definitions load only at session start, the user must start a new session before the new type becomes dispatchable.
2. For `inherit-parent (user-approved)`, confirm the dispatched type has no model binding (empty or `inherit`, or an unconfigured built-in) so the parent's model is the effective selection.
3. A project default is valid only after the user explicitly approves its exact effective value for the current task.

The optional reasoning effort maps to the definition's `thoughtLevel` field, which is honored only when a specific model is set. Model and `thoughtLevel` changes take effect in new sessions only; a running session does not hot-reload definitions.

If the approved selection cannot be represented by a loaded agent type, return to planning. Do not silently dispatch a differently modeled type and do not fall back to another value. The Core dispatch envelope still records the adapter-validated model selection; under ZCode it informs the worker of its bound model rather than overriding anything.

## `dispatch_worker`

Preconditions:

- the contract is `APPROVED` and records `protocol_version: "0.7"`, `host_adapter: "zcode"`, and `adapter_version: "0.4"`;
- the contract records a populated `workflow_revision`, `protocol_sha256`, and `adapter_sha256` matching the exact loaded Skill, Core protocol, and ZCode adapter files;
- no other write-capable subagent owns the worktree;
- model and permission validation passed;
- every applicable coding-rule path and Documentation obligation resolves;
- the required agent type is loaded in the current session (`lightweight_implementer` for an exact binding, or an `inherit`-bound definition for approved parent inheritance).

Dispatch that agent type exactly once, with `run_in_background` only when the Planner decides background execution and accepts notification-based progress. Pass the absolute contract path, the absolute loaded Core-protocol path, task id, revision, approved model selection, and absolute coding-rule component paths in this instruction envelope:

```text
Execute approved contract <absolute-path>.
Read and follow result protocol <absolute-core-protocol-path>.
Task: <task-id>, revision <revision>.
Model selection: <adapter-validated-selection>.
Before editing, read every Applicable coding rules path from the contract.
Treat the contract as the sole authority.
Do not ask the user, expand scope, edit the contract, or spawn another agent.
Return exactly one STATUS: DONE, STATUS: BLOCKED, or STATUS: FAILED result using the referenced schema, including DOCUMENTATION evidence.
```

Before dispatching, `dispatch_worker` recomputes the SHA-256 digests of the loaded Skill (`SKILL.md`), `references/protocol.md`, and this adapter reference, using the Core's canonical UTF-8/LF text representation. It rejects missing, placeholder, mismatched, or stale contract evidence before any worker is started; a changed source requires a new approved contract revision.

## `inherit_permissions`

The worker inherits the main task's live sandbox and approval policy. Keep `model: inherit` in the model-neutral implementation Agent so per-task choices remain authoritative; a specific model binding requires a purpose-built definition (for example `lightweight_implementer_flash`), and creating one is a planning-time proposal requiring a new session. The Scout Agent's read-only definition is a required narrowing, not a permission broadening.

Use ZCode approval controls for in-scope operations that need elevation. A denied or unavailable permission that prevents acceptance is `BLOCKED`; the adapter never changes configuration to bypass it.

## `control_lifecycle`

Before dispatch, confirm single-writer ownership. Continue the same subagent for a limited in-scope repair or an approved contract revision by resuming its `agent_<uuid>` id or by a fresh dispatch after the earlier writer is confirmed closed. If the user changes material requirements, stop the worker with `TaskStop` (or wait for completion) before planning resumes.

A replacement is permitted only after the earlier writer is confirmed stopped, completed, or closed. Ambiguous ownership is blocking because another spawn could violate the one-writer invariant.

## `report_progress`

Observe a background implementation task through ZCode's `TaskOutput` (blocking with timeout, or non-blocking) and its completion notification. Keep command logs and intermediate implementation details in that task. Relay only concise progress or a decision-requiring block to the user. Progress observation never authorizes another writer.

## `relay_result`

Receive the worker's final message as the Agent tool result. Validate:

- the first line is exactly one Core status;
- all sections required by that status are present;
- changed paths, command exits, and acceptance evidence are explicit for `DONE`;
- `DOCUMENTATION` reports the decision, canonical document and index, navigation, validation, and freshness evidence;
- missing evidence is not described as success.

The Planner may perform read-only confirmation. In-scope repair returns to the same worker; the Planner does not edit product code.

## `manage_version_control`

Inputs are the approved contract's Version control section: system, baseline, logical commit boundary, Changelog disposition and proposed entry, proposed Conventional Commit message, commit authority, push authority, and any exact push target.

For `version_control_system: none`, run no Git command and return not-applicable evidence. For Git, establish or revalidate the baseline with read-only commands scoped to the resolved repository:

```text
git rev-parse --show-toplevel
git branch --show-current
git rev-parse HEAD
git status --short --untracked-files=all
git diff --cached --name-status
```

Record branch or detached state, revision, staged paths, and uncommitted paths. Do not use a nominally diagnostic command that writes the index, `HEAD`, refs, configuration, or object database. A baseline change or staged path outside the approved logical boundary is `BLOCKED` when safe continuation would require touching user work or revising the contract.

When commit authority is `none`, do not run `git add`, `git commit`, or `git push`; report the approved proposed message. When the contract grants exact commit authority:

1. Revalidate `HEAD`, the index/staged state, worktree ownership, allowed paths, required feature documentation, and required Changelog entry.
2. Stage only contract-authorized paths with `git add -- <exact-paths>` or, for an authorized mixed file, `git add -p -- <exact-path>`.
3. Inspect `git diff --cached --stat` and `git diff --cached`; reject unrelated content, missing required artifacts, secrets, temporary files, or a non-atomic boundary.
4. Validate the exact approved message against the canonical Conventional Commit rules, then execute one `git commit` with that message.
5. Record the resulting full SHA and message, then inspect `git status --short` for the post-commit state.

Do not amend, squash, rebase, tag, rewrite history, or replace the current index as part of this operation. If safe exact staging cannot preserve unrelated staged or working changes, return `BLOCKED` before mutation.

Push is separate. Run `git push <approved-remote> <approved-source>:<approved-destination>` only when the contract grants exact push authority for that remote and refspec and the committed SHA matches the authorized logical change. Otherwise do not contact a remote. Commit authority never implies push authority.

Return the Core version-control evidence fields without rewriting status. A denied authority, ownership conflict, or contract mismatch is `BLOCKED`; an evidence-backed failure of an authorized operation that cannot progress under the same environment is `FAILED`.

## Optional PLAN-task capability: verified mapping

The verified mapping uses the ZCode read-only Agent mechanism: one `Explore`-type subagent (or a custom read-only scout definition binding the approved PLAN model) per micro or batch task, with the exact task envelope and an explicit model binding. The host enforces read-only access for the `Explore` type; the task receives only its exact source selectors/query, policy limits, stop conditions, and Evidence Packet response contract. It receives no complete parent transcript and has no write, external-mutation, decision, contract, or spawn authority.

### Live evidence recorded 2026-09-04

The parent Planner ran one real `Explore`-type micro `repository-read` task with an approved scout model binding on the ZCode `cli` surface. The task received only the bounded task envelope, returned an Evidence Packet accepted by `scripts/validate_evidence_packet.py` with exit `0`, and used no expansion. Pre/post `HEAD`, staged state, worktree status, and changed-path inventory were byte-for-byte identical.

This evidence verifies the ZCode micro-task isolation, model binding, result relay, no-expansion path, and unchanged-worktree path. It does not by itself exercise expansion handling, batch scheduling/concurrency, every supported host surface, or WORK dispatch; those remain governed by the corresponding operation checks and fallback rules.

The adapter therefore declares `read_only_scout_dispatch`. Direct PLAN handling remains the fallback when the host cannot provide this verified mechanism or when policy limits are exceeded. A future adapter or broader capability claim requires its own retained evidence and versioned metadata revision.

## Verification basis

This `VERIFIED` mapping preserves main-task planning, explicit per-task implementation-model choice, the model-neutral `lightweight_implementer`, inherited permissions, one subagent writer, documentation-aware result relay, and the user-level Skill plus Agent installation layout. Protocol `0.7` validation checks adapter metadata, all nine operation mappings, the WORK write gate, task-envelope policy, bundled-rule integrity, feature-documentation integration, and source/install parity. The optional PLAN-task mapping is verified for the recorded ZCode micro-task path and remains independent of WORK writer authorization.
