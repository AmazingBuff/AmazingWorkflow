# Two-Phase Coding Core Protocol

Protocol version: `0.3`.

This document defines the host-neutral contract, state, worktree, single-writer, and result rules. Host detection and execution mappings belong to the [Host Adapter Contract](adapter-contract.md) and the selected adapter reference.

## Core invariants

- One user-facing Planner owns requirements, approval, and final reporting.
- One implementation worker owns product-code writes to a worktree.
- The workflow has exactly two phases: planning and implementation.
- No product-code write occurs before contract and implementation-model approval.
- An approved contract is the sole implementation authority and is never edited in place.
- Model selection is explicit and is never silently substituted.
- Permissions may be inherited or narrowed, never broadened by this workflow.
- Version-control mutations require exact, separately recorded authority; contract or implementation approval alone grants none.
- `DONE`, `BLOCKED`, and `FAILED` are the only implementation result states.

## Contract rules

Create each contract from `../assets/implementation-contract.md`. The selected host adapter supplies the task-record location and any host-specific path conventions; the Core does not prescribe a storage path.

Use a short, filesystem-safe task id. Do not put secrets, personal data, or proprietary request text in it.

### Required contract properties

- `status` is `APPROVED` before dispatch.
- `revision` is a positive integer.
- `protocol_version` matches this Core protocol.
- `host_adapter` identifies the single selected verified adapter.
- `adapter_version` matches the adapter used for approval and dispatch.
- Every requirement has a stable `R-<number>` id.
- Every acceptance criterion has a stable `AC-<number>` id.
- Every requirement maps to at least one acceptance criterion.
- `allowed_paths` is narrow enough to prevent an implicit repository-wide rewrite.
- Existing user changes that must be preserved are identified in the baseline or constraints.
- Verification commands are real project commands, or the contract states why a check is manual.
- `implementation_model` is the exact user-approved value. Parent inheritance is recorded only as `inherit-parent (user-approved)`.
- The Version control section records `git` or `none`. A Git-backed task also records the read-only baseline, one logical commit boundary, Changelog decision and proposed entry, proposed Conventional Commit message, commit authority, and separate push authority.
- Commit authority and push authority default to `none`. Any granted authority names the exact action and scope; push authority also names the remote and refspec.
- Open product or architecture questions make the contract ineligible for approval.

The adapter owns the host-specific representation and validation of the approved model value. The Core defines no model catalog or fallback order.

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
- implementation model, reasoning effort, host adapter, or adapter version.

Do not overwrite an approved contract. Mark an old revision `SUPERSEDED` only after its replacement is approved, and link the revisions through `supersedes`.

A clarification that changes none of the items above may be relayed to the same worker without a new revision, but it must be recorded in the task result.

## Two-phase state model

The Core exposes only these phases:

1. `PLANNING`: discover, clarify, validate capabilities, prepare a contract, and obtain approval.
2. `IMPLEMENTING`: dispatch one worker, execute within the contract, verify, and return one result.

Internal host states do not create a third phase or another decision-making role.

## Dispatch envelope

The Planner supplies the implementation worker with:

- the absolute approved-contract location;
- the absolute or host-resolvable location of this Core protocol;
- task id and contract revision;
- the adapter-validated implementation model and optional reasoning effort;
- an instruction to treat the contract as the sole authority;
- an instruction not to ask the user, expand scope, or create another writer;
- an instruction to return exactly one result schema from this document.

The selected adapter defines how that envelope is represented and dispatched.

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

The worker must not:

- ask the user or make product decisions;
- alter the contract or reinterpret an unresolved requirement;
- expand behavior, architecture, dependencies, public interfaces, or allowed paths;
- modify unrelated code for cleanup;
- create another writer;
- stage, commit, push, deploy, publish, delete data, or perform external writes without explicit contract authority.

### Version-control rules

For a Git-backed task, the worker reads and follows the canonical [Git commit and Changelog convention](git-commit-convention.md). It preserves the recorded baseline and logical change boundary throughout implementation.

- Maintain every required Changelog entry with the implementation, tests, documentation, and configuration that form the same logical change. If no entry is required, record the policy reason; never omit an entry merely because no Changelog file exists.
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
4. changed files;
5. acceptance evidence;
6. commands and test results;
7. version-control system and baseline, Changelog disposition, commit status or proposed message, and push status;
8. unverified items and risks;
9. contract location and revision.

The Planner may inspect the diff and rerun read-only checks, but may not edit product code.
