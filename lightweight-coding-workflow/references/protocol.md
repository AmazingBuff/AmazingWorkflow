# Two-Phase Coding Core Protocol

Protocol version: `0.7`.

This document defines the host-neutral contract, two public control phases,
task-capability envelopes, worktree, single-writer, documentation, and result
rules. Host detection and execution mappings belong to the [Host Adapter
Contract](adapter-contract.md) and the selected adapter reference. PLAN routing
belongs to the [Context Routing reference](context-routing.md).

## Core invariants

- One user-facing Planner owns requirements, approval, and final reporting.
- One implementation worker owns product-code writes to a worktree.
- The workflow has exactly two public control phases: `PLAN` and `WORK`. Direct inspection and read-only PLAN tasks are activities inside PLAN, not a third phase or a second writer.
- No PLAN task dispatch occurs before the Planner records the exact task model, task count, and token ceiling in the authorization envelope.
- No product-code write occurs before contract and implementation-model approval.
- Only a compatible adapter with `support_state: VERIFIED` may dispatch product-code writes. PLAN-task dispatch is a separate, optional read-only adapter capability and never authorizes writes.
- An approved contract is the sole implementation authority and is never edited in place.
- Model selection is explicit for every dispatched role (PLAN tasks and WORK worker) and is never silently substituted.
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
- The Discovery section records the routing decision (`direct`, `micro`, or `batch`), its context-economics basis, delegated input and result estimates, and the evidence-locator index used by requirements and acceptance criteria. Requirements and acceptance criteria should reference surviving locators (`path:symbol`, `path:lines a-b`) so the worker starts from precise coordinates.
- A micro or batch Discovery section records the exact PLAN-task model, task count, token ceiling, and whether dispatch occurred. A direct record has no task packet. The record must state that total-token savings are not inferred.
- Stable symbols, sections, objects, and source content identity are preferred over ordinary line ranges. Use a line range only when necessary and pair it with a source revision or digest when staleness matters.
- Applicable bundled coding-rule component documents are recorded one host-resolvable absolute path per entry, or the section records `None`; the worker loads every listed document before its first edit.
- The Version control section records `git` or `none`. A Git-backed task also records the read-only baseline, one logical commit boundary, Changelog decision and proposed entry, proposed Conventional Commit message, commit authority, and separate push authority.
- The Documentation section records Documentation Impact as `create`, `update`, or `not-required` with a canonical policy reason. For required maintenance it also records the canonical feature-document path, feature-index path, code and test entry points, required sections, and validation obligations; non-required fields use explicit safe not-applicable values.
- Commit authority and push authority default to `none`. Any granted authority names the exact action and scope; push authority also names the remote and refspec.
- Open product or architecture questions make the contract ineligible for approval.

The adapter owns the host-specific representation and validation of the approved model value. The Core defines no model catalog or fallback order.

The Planner must not mark a contract `APPROVED` until the workflow revision, protocol digest, and adapter digest are populated and verified against the exact resources selected for that task.

Workflow revision `0.7.1` uses Core protocol `0.7`, schema `2.1`, and
configuration revision `3`; adapter versions change only when their mapping or
metadata changes. Text-resource digests use canonical UTF-8/LF text:
decode UTF-8, normalize CRLF and lone CR to LF, re-encode UTF-8, then hash with
SHA-256. Configuration, protocol, and adapter text use this representation;
binary and generated packet artifacts retain raw-byte hashing. Existing
approved `0.6.x` contracts remain immutable and continue only with their
matching historical resources; they are not revalidated against current `0.7.1`
files.
New `0.7.1` contracts require `workflow_revision`, `protocol_sha256`, and
`adapter_sha256` before approval or dispatch. Approved `0.7.0` contracts remain
historical and are continued only with matching `0.7.0` Skill, schema,
configuration, Core, and adapter resources.

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

The Core exposes only these public phases:

1. `PLAN`: discover directly or through bounded read-only Evidence Task Agents per the [Context Routing reference](context-routing.md), clarify, validate capabilities, prepare a contract, and obtain approval.
2. `WORK`: dispatch one implementation worker, execute within the contract, verify, and return one result.

Internal host states do not create a third phase or another decision-making
role. Evidence Task Agents are read-only helpers inside `PLAN`; they are not a
phase, a writer, or a planner. The implementation Agent is a WORK capability,
not an owner of the WORK phase's decisions.

## PLAN task envelope

The minimal micro-task envelope is defined by
`assets/context-routing/orchestration-plan.schema.json` and contains one
supported read-only `task_kind`, exact source descriptors and query, budget,
stop conditions, context-economics record, the pre-authorized PLAN policy,
and the Evidence Packet response contract. It has no full parent transcript,
write authority, external mutation authority, scope-decision authority,
contract-authoring authority, or spawn authority.

Batch PLAN work uses the same task-kind and policy fields inside the validated
batch plan. A batch may contain multiple independent tasks and dependency
layers, but each layer is bounded by the policy's maximum concurrency.

Every delegated routing record must include:

- estimated Planner-context savings;
- estimated delegated input tokens and result size;
- coordination overhead and weighted-cost rationale;
- explicit evidence that the task is independently describable; and
- an explicit caveat that total-token savings are not claimed.

The pre-authorized Codex PLAN policy is `gpt-5.6-luna/max`, at most two
concurrent read-only tasks, at most 12,000 estimated input tokens per PLAN
round, no complete parent transcript, no writes or external mutations, one
user-visible dispatch notice, and no per-task approval while in policy.
Exceeding it requires user approval or direct fallback.

### PLAN External Research Gate

Every non-trivial coding proposal carries an `external_research` gate with a
`required`, `recommended`, or `not-required` decision, an explicit reason, a
status, and a search mode. The gate records decision-critical and
architecture-relevant flags, the evidence bar, source ids and citations,
limitations, uncertainty, risk, stop conditions, conflicts, and the host's
managed-web-research capability status.

Research is required for external APIs/ABIs/frameworks, runtime or version
compatibility, low-level hooks or integration patterns, new dependencies,
license-sensitive reuse, and locally unsupported designs with likely mature
prior art. Trivial/mechanical work, or a change fully determined by local code,
tests, and canonical documentation, may be marked not-required. Required
decision-critical research must be satisfied before approval. Unavailable,
disabled, or insufficient required evidence is a `BLOCKED` PLAN outcome, not
permission to invent a mature design. Recommended research can use an explicit
uncertain fallback with a recorded limitation and risk.
A `pending` gate may dispatch an eligible verified read-only research task with
its exact query and budget, but that dispatch is not approval evidence. A
decision-critical proposal or implementation contract still requires
`satisfied` research. The task may return newly discovered external source
records with complete provenance for Planner review; a local task in a mixed
batch returns an empty `external_sources` array and `not-required`/`none`
research result.
For `web_research.requested=true`, only the exact authorized query/questions,
mode, budget, and stop conditions are executable scope. URLs discovered by
that managed query are in-scope evidence and need no per-result expansion
approval; any additional query, domain, or scope requires an expansion request.
Discovery grants no download, reuse, copying, write, or mutation authority.

External source descriptors record a stable id, direct URL, source kind,
repository/project, revision when available, retrieval date, license/reuse
status, target-version/runtime applicability, relevant locator, confidence, and
conflicts. The normal architecture bar is authoritative upstream evidence plus
a maintained implementation, or an explicit reason why only one source exists.
Cached/indexed search is the default for established patterns; live search is
required when freshness, current release/branch, issue state, or compatibility
may have changed. Stop at the evidence bar, after contradictions are
resolved/disclosed, when marginal value falls below cost, or at the budget.

Only read-only `requirement-research` and `dependency-check` PLAN tasks may
receive the explicit managed web-search capability. It must distinguish managed
search from shell networking and carry `shell_network=false`,
`external_mutations=false`, and no download, remote execution, authentication,
dependency changes, copying, or GitHub mutation. A host capability is not
verified from documentation alone; the parent Planner may promote it only with
a bounded live read-only forward test. Direct Planner search is the fallback.
WORK does not perform scope-changing architecture research and returns to PLAN
when missing external evidence would alter the approved contract.

## WORK dispatch envelope

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

When an adapter provides optional read-only PLAN-task dispatch, the Evidence
Task result is an Evidence Packet, not a Core implementation result. The
packet shape is defined by `assets/context-routing/evidence-packet.schema.json`
and validated by `scripts/validate_evidence_packet.py`; every generated task
packet must carry both references so the response envelope cannot drift. The
optional adapter mapping is eligible only after live task isolation, model,
relay, and no-write evidence is retained. The Codex mapping records that
evidence for its tested micro path. The task response contract must
enumerate finding severity (`low`, `medium`, `high`, `critical`), finding
confidence (`low`, `medium`, `high`), fact fields (`id`, `statement`,
`provenance`, `confidence`), and fact confidence (`confirmed`, `inferred`,
`unverified`).

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
4. routing decision, PLAN-task model, and measured discovery token spend when micro or batch delegation ran;
5. changed files;
6. acceptance evidence;
7. commands and test results;
8. Documentation Impact, canonical document and index paths, navigation and validation evidence, and freshness status;
9. version-control system and baseline, Changelog disposition, commit status or proposed message, and push status;
10. unverified items and risks;
11. contract location and revision.

The Planner may inspect the diff and rerun read-only checks, but may not edit product code.

## Protocol 0.7 compatibility

Protocol `0.7` keeps the two-phase Core and single-WORK-writer invariant while
making PLAN routing task-capability based. It adds the direct/micro/batch
routing record, the minimal micro-task envelope, context-economics accounting,
the pre-authorized Codex PLAN policy, and the conditional External Research
Gate with source provenance and managed-search boundaries. The optional adapter capability is
still named `read_only_scout_dispatch` for metadata compatibility, but its
semantics are task-scoped Evidence Task dispatch. A same-version adapter
without that optional capability remains eligible for WORK and uses direct
PLAN handling. Approved `0.6.x` contracts remain immutable and continue only
with matching historical Core, Skill, adapter, schema, and configuration
resources; no `0.7` resource is paired with an older contract implicitly.
