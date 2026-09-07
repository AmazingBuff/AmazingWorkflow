---
host_adapter: "workbuddy"
host_id: "workbuddy"
display_name: "WorkBuddy Host Adapter"
protocol_version: "0.7"
adapter_version: "0.2"
support_state: "VERIFIED"
supported_surfaces:
  - "desktop"
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
verified_on: "2026-09-04"
---

# WorkBuddy Host Adapter

Implementation dispatch eligibility: **yes**, only after contract/model approval and immediate capability revalidation, and only on the `desktop` surface. Read [Known host limitations](#known-host-limitations-measured-2026-09-04) before relying on this adapter: WorkBuddy dispatch is synchronous, exposes no host-enforced permission narrowing, and cannot validate an exact model ID.

This reference maps the [Host Adapter Contract](../adapter-contract.md) and [Core protocol](../protocol.md) onto the WorkBuddy desktop host. All nine required operations were exercised live in an isolated promotion fixture on 2026-09-04; the evidence is recorded below. Three operations are satisfied in a **degenerate but coherent** form imposed by the host rather than by this mapping, and those limits are stated explicitly rather than hidden.

This adapter does **not** declare `read_only_scout_dispatch`. WorkBuddy is therefore limited to **direct PLAN handling**. See [Optional capability: why it is not declared](#optional-capability-why-it-is-not-declared).

It also does not declare `managed_web_research`. The PLAN capability check
records managed search as unavailable on this host until a future adapter
revision proves host-enforced read-only service access with a live forward
test. The gate consequently uses direct Planner search, an explicit uncertain
fallback, or `BLOCKED` and never shell networking.

## Compatibility

| Item | Mapping |
| --- | --- |
| Core protocol | Exact version `0.7` |
| Adapter | `workbuddy` version `0.2` |
| Planner | Current WorkBuddy main task and its session model |
| Worker | WorkBuddy user-level custom subagent `lightweight_implementer` |
| Worker source | `~/.workbuddy/agents/lightweight_implementer.md` (Markdown agent definition) |
| Custom-agent root | `~/.workbuddy/agents/` — the host registers `*.md` here as `subagent_type` values |
| PLAN task | Not declared. Direct PLAN handling only. |
| Contract asset | Loaded Skill's `assets/implementation-contract.md` |
| Feature documentation | Loaded convention and template plus contract-selected repository paths |
| Coding-rule components | Loaded Skill's `assets/coding-rules/**`, listed by absolute path in the contract |
| Task records | Repository-local `.lcw/task-runs/<task-id>/implementation-contract-v<revision>.md` |
| Result schemas | Core `DONE`, `BLOCKED`, and `FAILED` Markdown schemas with `DOCUMENTATION` evidence |

Task records use `.lcw/` rather than `.workbuddy/` because the host reserves `.workbuddy/` for its own project data (conversation memory and indices). Never write workflow records into `.workbuddy/`.

## Operation map

| Capability | Operation | WorkBuddy mechanism | Current failure mapping |
| --- | --- | --- | --- |
| Host identification | `identify_host` | Read host-provided context: product identity `WorkBuddy`, OS/shell signals, workspace folder, config root `~/.workbuddy/`, Skill catalog `~/.workbuddy/skills/`, and the WorkBuddy tool surface. | `CAPABILITY_UNAVAILABLE` if identity is absent or ambiguous. |
| Planner binding | `bind_planner` | Keep the current main task as Planner; resolve Skill resources from `~/.workbuddy/skills/lightweight-coding-workflow/` and task records from the repository root under `.lcw/`. | `CAPABILITY_UNAVAILABLE` if resources cannot be resolved. |
| Model validation | `validate_model` | The subagent `model` parameter. Documented routing values: `default` (inherit parent), `lite`, `reasoning`. | Return to planning for an exact model ID; never substitute. `CAPABILITY_UNAVAILABLE` for implementation while this adapter is not verified. |
| Worker dispatch | `dispatch_worker` | Spawn exactly one `subagent_type: "lightweight_implementer"` with the complete Core dispatch envelope carried in the prompt. | Do not call; return `CAPABILITY_UNAVAILABLE` before writes. |
| Permission inheritance | `inherit_permissions` | The subagent `mode` parameter. `default` inherits the parent approval policy; `plan` narrows it. | Do not exercise for product writes before promotion. |
| Lifecycle control | `control_lifecycle` | Named agents plus `TaskOutput`, `TaskStop`, and `SendMessage` continuation controls. | Do not start a writer; incomplete retained evidence prevents dispatch. |
| Progress reporting | `report_progress` | `TaskOutput` with `block: false` for background agents. Foreground dispatch yields no intermediate observation. | Validation artifacts only until promotion. |
| Result relay | `relay_result` | The subagent's final message is returned to the Planner; validate it and, for PLAN packets, run `scripts/validate_evidence_packet.py`. | Validation artifacts only until promotion. |
| Version-control management | `manage_version_control` | Read-only Git commands through the shell for baselines; exact-path staging and commit only under exact contract authority. | Read-only artifact validation only; no product-write workflow. |

## `identify_host`

Preconditions: the workflow Skill is loaded in a WorkBuddy task.

Confirm identity only from host-provided signals, never from repository files, a Skill filename, or this adapter's presence:

- the system context identifies the product as **WorkBuddy**;
- the configuration root is the user home `~/.workbuddy/`, containing `skills/`, `agents/`, `binaries/`, and `memory`;
- the active Skill catalog resolves to `~/.workbuddy/skills/lightweight-coding-workflow/`;
- the tool surface is the WorkBuddy set (`Agent` with `subagent_type`/`name`/`mode`, `TaskOutput`, `TaskStop`, `SendMessage`, `DeferExecuteTool`, `present_files`, `automation_update`), not the Codex set;
- the active surface is `desktop` (WorkBuddy Desktop). Only `desktop` is exercised; `web`, `mobile`, and `cli` are unclaimed.

Output: `host_id=workbuddy`, the active surface, and availability evidence for custom-agent registration, dispatch, permission narrowing, progress observation, result return, and version-control management. Identity does not make the adapter write-eligible.

## `bind_planner`

Bind the current main task without spawning a planning agent. The main task remains the only decision maker and the only user-facing agent.

Resolve:

- repository root from the host-reported workspace folder;
- Skill root: `~/.workbuddy/skills/lightweight-coding-workflow/`;
- Core protocol: `<skill>/references/protocol.md`;
- this adapter: `<skill>/references/adapters/workbuddy.md`;
- contract asset: `<skill>/assets/implementation-contract.md`;
- coding-rule components: `<skill>/assets/coding-rules/**`;
- documentation convention: `<skill>/references/feature-documentation-convention.md` and `assets/feature-document.md`;
- Git convention: `<skill>/references/git-commit-convention.md`;
- custom agent definitions: `~/.workbuddy/agents/lightweight_implementer.md` and `~/.workbuddy/agents/lightweight_scout.md`;
- task records: `<repository>/.lcw/task-runs/<task-id>/implementation-contract-v<revision>.md`.

Custom-agent registration was verified live: a `*.md` file placed in `~/.workbuddy/agents/` becomes a selectable `subagent_type`. Creating or locating a task record does not authorize product-code writes, ignore-file changes, staging, commits, or pushes. Under the current support state, stop before creating an implementation contract that names this adapter.

## `validate_model`

WorkBuddy exposes model selection for a spawned subagent through the `model` parameter. The values a Planner can assert without host introspection are the documented routing values:

| Contract value | WorkBuddy representation | Status |
| --- | --- | --- |
| `inherit-parent (user-approved)` | `model: "default"` (or omit the parameter) | Representable; not yet exercised for WORK |
| Routing preference | `model: "lite"` or `model: "reasoning"` | Representable; narrows cost/reasoning, not an exact model ID |
| Exact model ID | Not representable | Return to planning; never substitute |

There is no host mechanism by which the Planner can enumerate or confirm the exact model a subagent will run, and no reasoning-effort parameter exists. Therefore:

1. An exact model or reasoning-effort request cannot be validated. Return to planning and ask the user to approve `inherit-parent (user-approved)` or a routing value. Never silently substitute, and never edit the agent definition to force a model.
2. `inherit-parent (user-approved)` maps to `model: "default"`. Promotion must still confirm that no host-level default intervenes between the parent session model and the spawned worker.
3. Recording `implementation_model` in the contract as anything other than a user-approved exact value or `inherit-parent (user-approved)` makes the contract ineligible for approval.

Current protocol action: report `CAPABILITY_UNAVAILABLE` for implementation because model representability cannot override the support-state gate.

## `dispatch_worker`

Preconditions:

- the contract is `APPROVED` and records `protocol_version: "0.7"`, `host_adapter: "workbuddy"`, and `adapter_version: "0.2"`;
- the contract records a populated `workflow_revision`, `protocol_sha256`, and `adapter_sha256` matching the exact loaded Skill, Core protocol, and WorkBuddy adapter files;
- no other write-capable subagent owns the worktree;
- model and permission validation passed;
- every applicable coding-rule path and Documentation obligation resolves;
- `~/.workbuddy/agents/lightweight_implementer.md` exists and registers as `subagent_type`.

Current protocol action: **MUST NOT call the dispatch mechanism for product writes.** Return `CAPABILITY_UNAVAILABLE` before any writer starts. Filling the contract, obtaining user consent, or verifying only part of the checklist cannot change this action.

The promoted dispatch would look like this. Spawn exactly once, foreground, with `mode: "default"`:

```text
subagent_type: "lightweight_implementer"
name:          "lcw-<task-id>-v<revision>"
mode:          "default"          # inherit; never bypassPermissions or acceptEdits
model:         <validated selection or omitted>
run_in_background: false          # foreground keeps relay lossless
prompt:        <the envelope below>
```

The prompt must carry the complete Core dispatch envelope verbatim:

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

### Digest revalidation before dispatch

Recompute the canonical SHA-256 digests (UTF-8, CRLF and lone CR normalized to LF) of the loaded `SKILL.md`, `references/protocol.md`, and `references/adapters/workbuddy.md`, then compare them with the contract's `protocol_sha256` and `adapter_sha256`. On this host:

```bash
python - <<'EOF'
import hashlib, pathlib
paths = [
    "~/.workbuddy/skills/lightweight-coding-workflow/SKILL.md",
    "~/.workbuddy/skills/lightweight-coding-workflow/references/protocol.md",
    "~/.workbuddy/skills/lightweight-coding-workflow/references/adapters/workbuddy.md",
]
for raw in paths:
    p = pathlib.Path(raw).expanduser()
    text = p.read_bytes().decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
    print(f"sha256:{hashlib.sha256(text.encode('utf-8')).hexdigest()}  {p}")
EOF
```

Reject missing, placeholder, mismatched, or stale evidence before any worker starts. A changed source requires a new approved contract revision.

## `inherit_permissions`

WorkBuddy carries subagent permissions in the `mode` parameter. **Measured on 2026-09-04: the `mode` parameter does not enforce read-only for subagents.** A worker dispatched with `mode: "plan"` successfully edited a file and returned `STATUS: DONE`, so the value is advisory in practice, not a sandbox.

| Value | Measured effect | Workflow use |
| --- | --- | --- |
| `default` | Inherits the parent session's approval policy; **verified** across all promotion-fixture workers | WORK worker default — the only value this adapter uses |
| `plan` | **Does not deny edit tools.** A `plan`-mode worker edited a file and completed successfully | Do not rely on it as a sandbox. It may still bias a model toward caution, which is not a guarantee |
| `dontAsk` / `auto` | Not measured; changes the approval surface | Forbidden |
| `acceptEdits` / `bypassPermissions` | Not measured; would broaden | **Forbidden.** Permissions may be inherited or narrowed, never broadened |

Consequences for this capability:

1. The operation is satisfied by **preservation**: `mode: "default"` preserves the parent session's approval policy, which was verified for every promotion-fixture worker. Narrowing is not available as a host guarantee.
2. Read-only intent must be carried by the agent's developer instructions and by the dispatch prompt, and the Planner must verify non-mutation afterwards. Instructions are advisory, not enforcement — see [`relay_result`](#relay_result) for the same principle measured on Evidence Packets.
3. Because no host-enforced read-only sandbox exists, `read_only_scout_dispatch` remains undeclared.

The workflow never passes a broadening value. A denied or unavailable permission that prevents acceptance is `BLOCKED`; the adapter never reconfigures the host to bypass it.

## `control_lifecycle`

**Measured 2026-09-04.** WorkBuddy agent dispatch is synchronous: the `Agent` call blocks until the worker returns its final message. There is no running-agent handle to observe or interrupt, and `run_in_background: true` does not register an agent task — both attempts returned the result inline, and `TaskOutput` rejects the returned agent id with `Background task "agent-…" not found`.

| Control | Mechanism | Verification status |
| --- | --- | --- |
| Start | `Agent` with `subagent_type` and a stable `name` | **Exercised** — six worker dispatches in the promotion fixture |
| Continue / repair | `Agent` with `resume: "<agent-id>"` and a follow-up prompt; the same worker continues with its prior transcript | **Exercised** — the malformed-result repair below |
| Completion | The synchronous call returns exactly one final result | **Exercised** — `DONE`, `BLOCKED`, and `FAILED` all returned |
| Interrupt / stop | **Not available for agents.** `TaskStop` and `TaskOutput` apply to background *shell* tasks only; an agent task id is not registered with them. | Measured limitation, not a gap in the mapping |
| Replace | Confirm the prior writer has returned its final result, then spawn under a new `name` | **Exercised** — each fixture task dispatched a distinct writer after the prior one returned |

Because dispatch is synchronous, the interrupt/stop affordance is structurally moot during the dispatch window: the Planner is blocked waiting, so there is no live writer to interrupt. A writer that must stop does so by returning `BLOCKED` or `FAILED` from inside its own turn, which was verified. The limit matters only if a future host version makes agent dispatch asynchronous; that would be a new adapter version with its own evidence.

Before spawn, confirm single-writer ownership: the Planner records the worker `name` and refuses a second write-capable spawn while that name is live. Continue the **same** worker for an in-scope repair or a malformed result. A replacement is permitted only after the earlier writer is confirmed stopped, completed, or closed; ambiguous ownership is blocking, because another spawn could violate the one-writer invariant.

> Tool-surface correction: an earlier draft of this adapter named `SendMessage` as the continuation mechanism. `SendMessage` resolves to the Agent Mail email tool (`mcp__agent-mail__SendMessage`) on this host and is not an agent-to-agent channel. Continuation is `Agent` + `resume`.

## `report_progress`

**Measured 2026-09-04: WorkBuddy exposes no intermediate progress channel for agent workers.** Dispatch is synchronous (see [`control_lifecycle`](#control_lifecycle)), `run_in_background: true` does not register a pollable agent task, and `TaskOutput` reports `Background task "agent-…" not found` for a returned agent id. `TaskOutput` with `block: false` and `TaskStop` were both verified working, but only against background **shell** tasks, not agents.

The operation is therefore satisfied in a degenerate form, and this is a host characteristic rather than an adapter choice:

- there is no intermediate progress to observe, so nothing is observed;
- the protective invariant the operation exists for is fully preserved — raw command output, logs, and intermediate implementation detail stay inside the worker's own context and never enter the Planner's decision context;
- the Planner receives exactly one final result.

Consequence the user should know before choosing this adapter: a long implementation cannot be watched while it runs, and a worker that would run for a long time gives no progress signal until it returns. Prefer a contract whose verification is fast enough that the synchronous wait is acceptable.

Progress observation never authorizes a second writer.

## `relay_result`

The spawned agent's final message is returned to the Planner. Validate:

- the first line is exactly one Core status (`STATUS: DONE`, `STATUS: BLOCKED`, or `STATUS: FAILED`);
- every section required by that status is present;
- changed paths, command exit codes, and acceptance evidence are explicit for `DONE`;
- `DOCUMENTATION` reports the decision, canonical document and index, navigation, validation, and freshness evidence;
- missing evidence is not described as success.

For PLAN Evidence Packets, additionally run `scripts/validate_evidence_packet.py` and require exit `0`.

### Measured relay evidence

**2026-09-03 — PLAN Evidence Packet relay** (read-only promotion-fixture probes, `subagent_type: "lightweight_scout"`, `mode: "plan"`):

| Probe | Dispatch prompt | Validator result |
| --- | --- | --- |
| probe-01 | Full response contract restated in the prompt | `VALID`, exit `0` |
| probe-02 | Bare envelope, no behavioral instructions | Well-formed packet, not schema-checked |
| probe-03 | Corrected agent definition, bare envelope | `INVALID`, exit `2`, 10 schema errors |

These three are promotion-fixture observations of a capability this adapter does **not** declare (see [Optional capability](#optional-capability-why-it-is-not-declared)). They establish a rule the adapter relies on elsewhere; they do not authorize PLAN-task dispatch.

**2026-09-04 — WORK result relay** (isolated promotion fixture, `subagent_type: "lightweight_implementer"`, `mode: "default"`, six dispatches):

| Dispatch | Scenario | Result |
| --- | --- | --- |
| W1 | DONE with exact-path staging and commit authority | `STATUS: DONE`, full schema, commit `b17ea03`; independently re-verified |
| W1 `resume` | In-scope malformed-result repair | Same agent id `agent-d03302c3` re-emitted a complete corrected result; no file changed |
| W2 | Uncommitted user work overlapping the write scope | `STATUS: DONE`; user block preserved byte-identically (SHA-256 verified); no commit created |
| W3 | Dispatched with `mode: "plan"` | **Edited the file and returned `STATUS: DONE`** — `plan` does not enforce read-only |
| W4 | Divide-by-zero behavior left unspecified | First response was unparseable; `resume` repair returned `STATUS: BLOCKED`, category `behavior`, full schema |
| W5 | `version_control_system: none`, non-Git directory | `STATUS: DONE`; no Git command run, no repository initialized |
| W6 | Required tool absent, no remedy authorized | `STATUS: FAILED`, full schema with `ATTEMPTS` and `WORKTREE_STATE`; no workaround invented |

Conclusion, and a binding rule for this adapter: **a custom agent definition is advisory, not self-enforcing.** Its response-contract instructions materially improve compliance but do not guarantee it. Every dispatch prompt must restate the response contract, and the Planner must validate the returned artifact with the Skill's validator rather than trusting the shape.

All three Core result states were relayed losslessly from real workers, and the malformed-result repair path returned to the same worker rather than spawning a replacement.

Failure handling: continue the **same** worker via `Agent` + `resume` to repair an in-scope malformed result. If a second attempt still fails, or the failure is out of scope, return `FAILED`. The Planner may perform read-only confirmation but never edits product code.

## `manage_version_control`

Inputs are the approved contract's Version control section: system, baseline, logical commit boundary, Changelog disposition and proposed entry, proposed Conventional Commit message, commit authority, push authority, and any exact push target.

For `version_control_system: none`, run no Git command and return not-applicable evidence. For Git, establish or revalidate the baseline with read-only commands, run through the shell (Git Bash on Windows, forward slashes):

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

## Optional capability: why it is not declared

The candidate mechanism works: `Agent` with `subagent_type: "lightweight_scout"` dispatches a bounded read-only task and returns an Evidence Packet. Both blockers below were re-measured on 2026-09-04 and are independent of that mechanism; they cannot be resolved by consent or by a populated contract.

1. **No host-enforced read-only sandbox, and no effective narrowing.** Codex supplies `sandbox_mode = "read-only"` in the agent TOML. WorkBuddy has no equivalent, and the 2026-09-04 measurement is stronger than the 2026-09-03 one: a worker dispatched with `mode: "plan"` **edited a file and returned `STATUS: DONE`**, so `plan` is not a narrowing mechanism either. Read-only behavior on this host is instruction-based only. The contract requires that "the host enforces a read-only sandbox."
2. **No exact per-task model override.** `dispatch_scout` requires an "explicit validated model override." WorkBuddy cannot enumerate or confirm an exact subagent model (see [`validate_model`](#validate_model)), so an override can be requested but never validated.

The contract states the capability "must never be inferred from `worker_dispatch`, the presence of `lightweight_scout`, or documentation alone." It is therefore **not declared**, and PLAN uses direct handling: the Planner reads sources itself, or uses `lightweight_scout` only as an explicitly user-approved, non-workflow inspection aid whose output is validated and whose non-mutation is confirmed afterwards, because no host mechanism enforces it.

If WorkBuddy later exposes an enforced read-only subagent sandbox and a validatable exact model override, declare the capability in a new adapter version with its own retained live evidence.

## Known host limitations (measured 2026-09-04)

These are characteristics of the WorkBuddy host, not defects in this mapping. Each was measured, not assumed. Read them before relying on this adapter for a real task.

| # | Limitation | Evidence | Practical consequence |
| --- | --- | --- | --- |
| L1 | `mode` does not enforce permissions for subagents. A `plan`-mode worker edited a file and completed. | W3 returned `STATUS: DONE` after editing `calc.py` under `mode: "plan"` | Read-only intent must be carried by instructions and verified by the Planner afterwards. Never treat `plan` as a sandbox. |
| L2 | Agent dispatch is synchronous. `run_in_background: true` returned results inline twice and produced no pollable task; `TaskOutput` rejects the agent id. | Two dispatches returned inline; `TaskOutput` on `agent-3a5de2f0` returned `not found` | No progress visibility while a worker runs. Keep contracts' verification cheap enough that a blocking wait is acceptable. |
| L3 | A running agent cannot be interrupted or stopped. `TaskStop` and `TaskOutput` apply to background **shell** tasks only (verified working there: a 60 s shell task was polled at 5 s and killed at 10 s). | `TaskStop` killed shell task `GJYThl`; `TaskOutput` could not resolve agent `agent-3a5de2f0` | A worker stops only by returning `BLOCKED` or `FAILED` from inside its own turn. There is no external kill switch. |
| L4 | Exact model IDs and reasoning effort are not representable. The `model` parameter accepts documented routing values only, and there is no effort parameter. | See [`validate_model`](#validate_model) | Contracts must record `inherit-parent (user-approved)` or a routing value. An exact-ID request returns to planning. |
| L5 | Continuation is `Agent` + `resume`, not `SendMessage`. `SendMessage` resolves to the Agent Mail email tool on this host. | Tool search resolved `SendMessage` → `mcp__agent-mail__SendMessage` | Continue a worker with `resume: "<agent-id>"`. |

## Verification status (2026-09-04)

Exercised on `desktop`, Windows, adapter mechanisms `0.1`→`0.2` (no operation mechanism changed between them; `0.2` records the promotion and corrects documentation):

Host identification and planning

- [x] User-level custom subagent registration: `~/.workbuddy/agents/*.md` resolves as `subagent_type`, proven by a bare-envelope dispatch that returned a scout-shaped packet no generic agent would produce.
- [x] Host identification positive on WorkBuddy, with the active host distinguished from a coexisting Codex installation on the same machine (`~/.codex/` exists with its own copy of this Skill and its agents). Selection follows the live host context, not the presence of configuration directories.
- [x] Planner-only ownership: no planning agent was spawned; the main task authored every contract and every report.
- [x] Source/install parity: `check_install_parity.py` `MATCH`, exit `0`, re-verified after every probe and dispatch.
- [x] Package validation: `validate_plan.py` on the bundled example plan returns `VALID`, exit `0`; `validate_evidence_packet.py` accepted a relayed packet, exit `0`.

Dispatch and permissions

- [x] Exactly one WORK worker received the complete dispatch envelope and loaded both coding-rule documents before its first edit (W1; evidenced by rule-priority reasoning in its result).
- [x] Single-writer ownership maintained across six dispatches; no second writer ever spawned.
- [x] `mode: "default"` preserved the parent approval policy (W1–W6); no broadening value was ever passed.
- [x] **Measured correction:** `mode: "plan"` does **not** enforce read-only (W3 edited a file). Recorded as limitation L1 and used as the decisive reason `read_only_scout_dispatch` stays undeclared.
- [x] `inherit-parent (user-approved)` validated end to end as `implementation_model` on every dispatch.

Results and lifecycle

- [x] `STATUS: DONE` relayed losslessly with `DOCUMENTATION` and `VERSION_CONTROL` (W1, W2, W5).
- [x] `STATUS: BLOCKED` relayed losslessly with `CATEGORY`, `QUESTION`, `OPTIONS`, `RECOMMENDATION`, `CURRENT_STATE` (W4, after repair).
- [x] `STATUS: FAILED` relayed losslessly with `EVIDENCE`, `ATTEMPTS`, `WORKTREE_STATE`, `RECOMMENDED_NEXT_STEP` (W6).
- [x] Malformed result repaired by continuing the **same** worker via `Agent` + `resume` (W4: unparseable response → complete `BLOCKED` schema, same agent id).
- [x] Continuation via `resume` preserved prior context and produced no side effects (W1 repair: HEAD and index unchanged).
- [x] Confirmed-safe replacement: each fixture task dispatched a distinct writer only after the previous one had returned.
- [x] Interrupt/stop measured as unavailable for agents and available for shells (`TaskStop` killed a 60 s shell task at 10 s) — limitation L3.

Version control

- [x] Baseline inspection non-mutating: the read-only command set run five times left `HEAD`, `index`, refs, reflog count, and object directories byte-identical.
- [x] `version_control_system: none` ran no Git command and initialized no repository (W5, W6).
- [x] Missing commit authority prevented the commit (W2, W4: HEAD unchanged, empty staged diff) and reported the proposed message only where a boundary existed.
- [x] Missing push authority prevented any push: the local bare remote held no refs after W1 committed.
- [x] An isolated Git fixture proved exact-path staging of three authorized paths, staged-diff inspection, one compliant commit with the approved Conventional Commit message, clean post-commit state, and an untracked workflow-records directory left unstaged.
- [x] Existing uncommitted user work preserved byte-identically across overlapping write scope (W2, W3; SHA-256 verified).
- [ ] **Outstanding:** a *granted* push to the exact remote and refspec has not been exercised. Until it is, this adapter must not be granted push authority; commit authority alone is verified.

Capability gate

- [x] While this adapter was `EXPERIMENTAL`, no product write was ever dispatched: every write in this evidence is inside a disposable promotion fixture, and the write gate would have returned `CAPABILITY_UNAVAILABLE` for any product repository. That gate behavior is now moot for `VERIFIED` but was never bypassed during promotion.

## Known divergence: bundled Scout instructions vs. the authoritative schema

The bundled `agents/lightweight_scout.toml` describes the Evidence Packet fields in prose that does not match `assets/context-routing/evidence-packet.schema.json` and `scripts/validate_evidence_packet.py`. A scout following the TOML verbatim produces an `INVALID` packet. Observed divergences:

| Field | `lightweight_scout.toml` prose | Validator requirement |
| --- | --- | --- |
| `plan_id` | not mentioned | required, identifier pattern |
| `status` | not mentioned | required, one of `complete`, `partial`, `blocked` |
| `unknowns` | listed as a section | array of non-empty **strings** |
| `facts_for_parent[].provenance` | "the required fields id, statement, provenance, and confidence" | array of non-empty **strings** |
| `findings[].evidence[]` | "cites the exact source id and locator" | object requiring `source_id`, `locator`, **and `note`** |

The WorkBuddy copy at `~/.workbuddy/agents/lightweight_scout.md` has been corrected against the schema and adds a "Common rejection causes" section. The bundled TOML still carries the divergence; a Codex-side scout dispatched from it will fail validation until the TOML is corrected. Resolving this is a package fix outside this adapter's scope.

## Promotion basis

This adapter is promoted to `VERIFIED` for the `desktop` surface with adapter version `0.2`, protocol `0.7`. The mapping's operation mechanisms are identical to those exercised as `0.1`; `0.2` records the promotion and corrects documentation, including the permission-narrowing claim that measurement disproved.

Three operations are satisfied in a degenerate form imposed by the host and documented as limitations: `inherit_permissions` is satisfied by preservation rather than narrowing (L1), `report_progress` is satisfied by a synchronous channel with no intermediate observation (L2), and `control_lifecycle` has no interrupt/stop for agents (L3). None of the three hides writes, leaks raw logs into the Planner's decision context, or permits a second writer.

One checklist item remains open — granted push authority (above). The adapter is `VERIFIED` for commit-scoped work; a contract must not grant push authority until that item is exercised and this file is amended.

The [Scout instruction divergence](#known-divergence-bundled-scout-instructions-vs-the-authoritative-schema) is explicitly accepted as open: it affects the undeclared PLAN-task capability and the Codex host, not WORK dispatch on this host.
