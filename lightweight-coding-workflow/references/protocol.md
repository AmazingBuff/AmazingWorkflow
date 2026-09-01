# Two-Phase Coding Core Protocol

Protocol version: `0.6`.

This document defines the host-neutral contract, state, worktree, single-writer, documentation, and result rules. Host detection and execution mappings belong to the [Host Adapter Contract](adapter-contract.md) and the selected adapter reference. Phase 1 discovery routing belongs to the [Context Routing reference](context-routing.md).

## Core invariants

- One user-facing Planner owns requirements, approval, and final reporting.
- One implementation worker owns product-code writes to a worktree.
- The workflow has exactly two phases: planning and implementation. Read-only scouting is a Phase 1 activity, not a third phase or a second writer.
- No Scout dispatch occurs before the Planner records explicit discovery authorization with the exact scout model, packet count, and token ceiling.
- No product-code write occurs before contract and implementation-model approval.
- Only a compatible adapter with `support_state: VERIFIED` may dispatch product-code writes. Scout dispatch is a separate, optional adapter capability and never authorizes writes.
- An approved contract is the sole implementation authority and is never edited in place.
- Model selection is explicit for every dispatched role (scouts and worker) and is never silently substituted.
- Permissions may be inherited or narrowed, never broadened by this workflow.
- Version-control mutations require exact, separately recorded authority; contract or implementation approval alone grants none.
- Required feature documentation is implementation material in the same logical change, not another phase.
- `DONE`, `BLOCKED`, and `FAILED` are the only implementation result states.

## Contract rules

Create each contract from `../assets/implementation-contract.md`. The selected host adapter supplies the task-record location and any host-specific path conventions; the Core does not prescribe a storage path.

Use a short, filesystem-safe task id. Do not put secrets, personal data, or proprietary request text in it.

### Required contract properties

- `status` is `APPROVED` before dispatch.
- `revision` is a positive integer.
- `protocol_version` matches this Core protocol.
- `workflow_revision` is the exact revision of the loaded workflow Skill.
- `protocol_sha256` is a populated `sha256:<64-hex-digits>` digest of the exact Core protocol resource used for approval and dispatch.
- `host_adapter` identifies the single selected compatible `VERIFIED` adapter.
- `adapter_version` matches the adapter used for approval and dispatch.
- `adapter_sha256` is a populated `sha256:<64-hex-digits>` digest of the exact selected adapter resource used for approval and dispatch.
- Every requirement has a stable `R-<number>` id.
- Every acceptance criterion has a stable `AC-<number>` id.
- Every requirement maps to at least one acceptance criterion.
- `allowed_paths` is narrow enough to prevent an implicit repository-wide rewrite.
- Existing user changes that must be preserved are identified in the baseline or constraints.
- Verification commands are real project commands, or the contract states why a check is manual.
- `implementation_model` is the exact user-approved value. Parent inheritance is recorded only as `inherit-parent (user-approved)`.
- The Discovery section records the routing decision (`direct` or `orchestrated`), its basis, the scout model when the orchestrated lane ran, estimated and measured discovery token spend, and the evidence-locator index used by requirements and acceptance criteria. Requirements and acceptance criteria should reference surviving locators (`path:symbol`, `path:lines a-b`) so the worker starts from precise coordinates.
- An orchestrated Discovery section also records whether discovery was dispatched. Its authorization record must contain the exact scout model, packet count, and token ceiling; `dispatched: no` is required when no scheduler ran.
- Stable symbols, sections, objects, and source content identity are preferred over ordinary line ranges. Use a line range only when necessary and pair it with a source revision or digest when staleness matters.
- Applicable bundled coding-rule component documents are recorded one host-resolvable absolute path per entry, or the section records `None`; the worker loads every listed document before its first edit.
- The Version control section records `git` or `none`. A Git-backed task also records the read-only baseline, one logical commit boundary, Changelog decision and proposed entry, proposed Conventional Commit message, commit authority, and separate push authority.
- The Documentation section records Documentation Impact as `create`, `update`, or `not-required` with a canonical policy reason. For required maintenance it also records the canonical feature-document path, feature-index path, code and test entry points, required sections, and validation obligations; non-required fields use explicit safe not-applicable values.
- Commit authority and push authority default to `none`. Any granted authority names the exact action and scope; push authority also names the remote and refspec.
- Open product or architecture questions make the contract ineligible for approval.

The adapter owns the host-specific representation and validation of the approved model value. The Core defines no model catalog or fallback order.

The Planner must not mark a contract `APPROVED` until the workflow revision, protocol digest, and adapter digest are populated and verified against the exact resources selected for that task.

Workflow revision `0.6.2` retains Core protocol `0.6` and Codex Adapter `0.6`. It migrates text-resource digests from the prior `0.6.1` raw-byte semantics to canonical UTF-8/LF text: decode UTF-8, normalize CRLF and lone CR to LF, re-encode UTF-8, then hash with SHA-256. Configuration, protocol, and adapter text use this representation; binary and generated packet artifacts retain raw-byte hashing. Existing approved `0.6.1` contracts may continue with matching historical `0.6.1` resources; reapproval is required only to run a task under workflow revision `0.6.2` and its canonical UTF-8/LF text-digest semantics. New `0.6.2` contracts require `workflow_revision`, `protocol_sha256`, and `adapter_sha256` before approval or dispatch.

### Revision rules

Create a new revision when any of these changes:

- user-visible behavior;
- requirements or non-goals;
- architecture or public API;
- dependencies;
- allowed or forbidden paths;
- destructive-operation authority;
- acceptance criteria or verification obligations;
- version-control system, logical commit boundary, Changelog disposition, proposed commit message, commit authority, or push authority;
- Documentation Impact, policy reason, canonical document or index path, code or test entry points, required sections, or validation obligations;
- implementation model, reasoning effort, host adapter, or adapter version;
- the applicable coding-rules set;
- the Discovery section's routing decision, basis, or scout model.
- the workflow revision, protocol digest, or adapter digest evidence.

Do not overwrite an approved contract. Mark an old revision `SUPERSEDED` only after its replacement is approved, and link the revisions through `supersedes`.

A clarification that changes none of the items above may be relayed to the same worker without a new revision, but it must be recorded in the task result.

## Two-phase state model

The Core exposes only these phases:

1. `PLANNING`: discover (directly or through read-only scouts per the [Context Routing reference](context-routing.md)), clarify, validate capabilities, prepare a contract, and obtain approval.
2. `IMPLEMENTING`: dispatch one worker, execute within the contract, verify, and return one result.

Internal host states do not create a third phase or another decision-making role. Scout subagents are read-only discovery helpers inside `PLANNING`; they are not a phase, a writer, or a planner.

## Dispatch envelope

The Planner supplies the implementation worker with:

- the absolute approved-contract location;
- the absolute or host-resolvable location of this Core protocol;
- task id and contract revision;
- the adapter-validated implementation model and optional reasoning effort;
- the verified workflow revision, protocol digest, and adapter digest recorded by the approved contract;
- the absolute paths of every applicable coding-rule component document;
- an instruction to treat the contract as the sole authority;
- an instruction not to ask the user, expand scope, or create another writer;
- an instruction to return exactly one result schema from this document.

The selected adapter defines how that envelope is represented and dispatched.

The adapter must reject dispatch when any required revision or digest field is missing, still a draft placeholder, or does not match the exact loaded workflow, Core protocol, or selected adapter resource. This check occurs after approval as well as before the worker starts.

When an adapter provides read-only scouting, the Scout result is an Evidence Packet, not a Core implementation result. The packet shape is defined by `assets/context-routing/evidence-packet.schema.json` and validated by `scripts/validate_evidence_packet.py`; the generated task packet must carry both references so the response envelope cannot drift.

## Worktree ownership

Before implementation, record:

- repository root;
- branch or detached state;
- current revision when version control exists;
- current index and staged state when Git exists;
- current uncommitted paths;
- which pre-existing changes overlap or must be preserved.

Only one implementation worker may own writes to a worktree. A replacement is allowed only after the prior writer is confirmed stopped, completed, or closed.

The worker returns `BLOCKED` before touching overlapping user changes unless the approved contract explicitly authorizes working with them. It must not overwrite, move, reformat, revert, or delete unrelated user work.

## Implementation rules

The worker may read files, edit approved paths, and run in-scope formatting, build, static-analysis, test, and diagnostic tools. It may repair failures directly caused by the approved task when the repair remains within scope.

Before its first edit, the worker reads every coding-rule component listed by the contract. An empty rule set is recorded as `None`; the worker never discovers a runtime dependency on another workflow specification.

When Documentation Impact is `create` or `update`, the worker creates or updates the canonical feature document and feature index atomically with affected implementation, tests, necessary Changelog, and configuration. It validates the contract's document paths, code and test entry points, required sections, links, named symbols when applicable, and freshness obligations. Documentation explains durable intent and navigation; it never excuses unclear code, hidden coupling, or missing tests.

The worker must not:

- ask the user or make product decisions;
- alter the contract or reinterpret an unresolved requirement;
- expand behavior, architecture, dependencies, public interfaces, or allowed paths;
- modify unrelated code for cleanup;
- create another writer;
- stage, commit, push, deploy, publish, delete data, or perform external writes without explicit contract authority.

### Version-control rules

For a Git-backed task, the worker reads and follows the canonical [Git commit and Changelog convention](git-commit-convention.md). It preserves the recorded baseline and logical change boundary throughout implementation.

- Maintain every required Changelog entry and required feature document or index update with the implementation, tests, and configuration that form the same logical change. If a Changelog or feature document is not required, record the applicable policy reason; never omit either merely because its default file does not yet exist.
- Treat commit authority and push authority as `none` unless the approved contract grants each exact action separately. Approval of implementation, a model, an adapter, or the contract itself is not staging, commit, or push authority.
- With commit authority `none`, do not modify the index or `HEAD`; report the proposed Conventional Commit message instead.
- With explicit commit authority, call the selected adapter's `manage_version_control` operation, stage only the exact authorized paths, inspect the staged diff, validate the logical boundary and message, and commit only that boundary. Do not amend, squash, rebase, tag, or rewrite history unless separately authorized by the contract.
- Push only when the contract separately authorizes the exact remote and refspec. Commit authority never implies push authority.
- For a non-Git task, record `version_control_system: none`, skip Git commands, and report Git fields as not applicable.

Return `BLOCKED` when safe continuation requires a user decision, contract revision, new authority, unavailable permission or service, or touching overlapping user changes. Stop new modifications after identifying the blocker.

Return `FAILED` when evidence-based attempts show that the approved task cannot progress under the current contract and environment, and a user decision alone would not resolve it.

Return `DONE` only after implementing the approved scope and running every feasible verification item. Failed or skipped checks remain explicit.

## Result protocol

Return Markdown using exactly one schema. The first line is exactly `STATUS: DONE`, `STATUS: BLOCKED`, or `STATUS: FAILED`. Never mix statuses or describe missing evidence as success.

### `DONE`

```markdown
STATUS: DONE

SUMMARY:
<one concise outcome>

CHANGED_FILES:
- <path>: <purpose>

ACCEPTANCE_EVIDENCE:
- AC-01: PASS | FAIL | UNVERIFIED — <evidence>

COMMANDS:
- `<command>` — exit <code> — <result>

DOCUMENTATION:
- Decision: <create | update | not-required> — <policy reason>
- Canonical document: <repository-relative path | not-applicable>
- Feature index: <repository-relative path | not-applicable>
- Navigation: <code and test entry points checked, including path and symbol evidence | not-applicable — reason>
- Validation: <link, section, content, or repository check and result | not-applicable — reason>
- Freshness: <current | not-applicable — reason>

VERSION_CONTROL:
- System: <git | none>
- Baseline: <branch or detached state, revision, and index/staged state | not applicable>
- Changelog: <added | updated | not-required | not-applicable> — <path, category, entry, or policy reason>
- Commit: <not-authorized — proposed message | committed — SHA and message | not-applicable>
- Push: <not-authorized | not-run — reason | pushed — remote and refspec | not-applicable>

UNVERIFIED:
- None

RISKS:
- None
```

Use `None` explicitly when a section has no entries. Do not omit failed or skipped commands.

### `BLOCKED`

```markdown
STATUS: BLOCKED

CATEGORY:
<behavior | scope | architecture | dependency | worktree | permission | destructive-action | verification>

QUESTION:
<the decision only the Planner and user can make>

WHY_BLOCKING:
<why guessing would violate the contract>

OPTIONS:
- <option and impact>

RECOMMENDATION:
<recommended option and reason>

DOCUMENTATION:
- Decision: <create | update | not-required> — <policy reason or current unresolved state>
- Canonical document: <repository-relative path | not-applicable>
- Feature index: <repository-relative path | not-applicable>
- Navigation: <completed, pending, failed, or not-applicable evidence>
- Validation: <completed, pending, failed, or not-applicable evidence>
- Freshness: <current, stale, pending, or not-applicable — reason>

VERSION_CONTROL:
- System: <git | none>
- Baseline: <recorded baseline | not applicable>
- Changelog: <current disposition and evidence>
- Commit: <not-authorized, not-run, committed SHA, or not-applicable; include proposed message when uncommitted>
- Push: <not-authorized, not-run, pushed target, or not-applicable>

CURRENT_STATE:
- Completed: <work completed>
- Changed files: <paths or None>
- Verification: <state>
- Contract revision required: <yes or no>
```

The worker stops new modifications after deciding it is blocked.

### `FAILED`

```markdown
STATUS: FAILED

FAILURE:
<what failed and where>

EVIDENCE:
- <reproduction, command output summary, or error>

ATTEMPTS:
- <attempt and result>

DOCUMENTATION:
- Decision: <create | update | not-required> — <policy reason>
- Canonical document: <repository-relative path | not-applicable>
- Feature index: <repository-relative path | not-applicable>
- Navigation: <completed, failed, or not-applicable evidence>
- Validation: <completed, failed, or not-applicable evidence>
- Freshness: <current, stale, or not-applicable — reason>

VERSION_CONTROL:
- System: <git | none>
- Baseline: <recorded baseline | not applicable>
- Changelog: <current disposition and evidence>
- Commit: <not-authorized, not-run, committed SHA, or not-applicable; include proposed message when uncommitted>
- Push: <not-authorized, not-run, pushed target, or not-applicable>

WORKTREE_STATE:
- Changed files: <paths or None>
- Safe to continue: <yes or no, with reason>

RECOMMENDED_NEXT_STEP:
<specific next action>
```

Use `FAILED` when more work with the same contract and environment is not producing new evidence. Use `BLOCKED` when a user decision, authority change, or contract revision can unblock the task.

## Planner completion report

For `DONE`, the Planner reports:

1. outcome;
2. implementation model;
3. selected host adapter and version;
4. routing decision, scout model, and measured discovery token spend when the orchestrated lane ran;
5. changed files;
6. acceptance evidence;
7. commands and test results;
8. Documentation Impact, canonical document and index paths, navigation and validation evidence, and freshness status;
9. version-control system and baseline, Changelog disposition, commit status or proposed message, and push status;
10. unverified items and risks;
11. contract location and revision.

The Planner may inspect the diff and rerun read-only checks, but may not edit product code.

## Protocol 0.6 compatibility

Protocol `0.6` adds Context Routing to `0.5`: a routing decision and optional read-only scout dispatch in Phase 1, the Discovery contract section, and the optional `read_only_scout_dispatch` adapter capability. The nine `0.5` capabilities are unchanged; adapters updated for `0.6` keep their `0.5` mappings and may add the optional capability. Approved `0.5` contracts remain immutable: continue them with their matching historical Core and adapter resources, or create and approve a new `0.6` revision. Do not pair a `0.6` Core with older adapter metadata through an implicit compatibility range. An exact same-version adapter without the optional capability remains eligible for implementation and restricts the Planner to the fast lane; older metadata is incompatible and is rejected before approval.
