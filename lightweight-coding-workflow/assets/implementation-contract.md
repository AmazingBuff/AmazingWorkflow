---
task_id: "{{TASK_ID}}"
revision: {{REVISION}}
status: "DRAFT"
created_at: "{{ISO_8601_TIMESTAMP}}"
supersedes: null
workflow_revision: "0.7.1"
protocol_version: "0.7"
protocol_sha256: null
host_adapter: null
adapter_version: null
adapter_sha256: null
implementation_model: null
reasoning_effort: null
approved_at: null
approval_summary: null
repository_root: null
baseline_revision: null
---

# Implementation Contract: {{TASK_TITLE}}

## Objective

{{ONE_VERIFIABLE_OBJECTIVE}}

## Discovery

- Routing: `direct`
- Basis: {{FILES_AND_TOKEN_ESTIMATE_OR_OTHER_ROUTING_BASIS}}
- PLAN-task model: `not-applicable`
- PLAN-task authorization: `not-applicable` for this safe direct-lane draft
- Authorized packet count: not-applicable
- Authorized token ceiling: not-applicable
- Discovery token spend: not-applicable
- Dispatched: `no`
- Evidence-locator index: not-applicable

Requirements and acceptance criteria below reference surviving stable locators (`path:symbol`, `path:section`, `path:object`, or `path:lines a-b` only when necessary) from this index so the worker starts from precise coordinates. Prefer source revision or content identity over ordinary line ranges when staleness matters. PLAN routing may be `direct`, `micro`, or `batch`; a micro task is a minimal single-task envelope and a batch retains the full orchestration plan. This template is a safe draft and must be populated and changed to `APPROVED` only after the approval gate. Before approval, replace the workflow/protocol/adapter revision placeholders and null digests with verified values from the exact loaded resources; an `APPROVED` contract may not retain placeholders or nulls.

## Requirements

- R-01: {{REQUIRED_BEHAVIOR}}

## External Research Gate

- Decision: `{{required | recommended | not-required}}`
- Reason: `{{EXPLICIT_REASON_FOR_THE_DECISION}}`
- Status: `{{satisfied | pending | unavailable | disabled | insufficient | blocked | not-required}}`
- Mode: `{{cached-indexed | live | direct-planner | none}}`
- Decision-critical: `{{true | false}}`
- Architecture-relevant: `{{true | false}}`
- Evidence bar: `{{authoritative-plus-maintained | authoritative-only-with-reason | context-only | not-applicable}}`
- Target applicability: `{{target versions, runtimes, and notes}}`
- Evidence/source records: `{{STABLE_SOURCE_IDS_URLS_REVISIONS_DATES_LICENSES_APPLICABILITY_LOCATORS_CONFIDENCE_AND_CONFLICTS_OR_NONE}}`
- Limitation: `{{EXPLICIT_LIMITATION_OR_NONE}}`
- Uncertainty and risk: `{{EXPLICIT_UNCERTAINTY_AND_RISK}}`
- Search stopping conditions: `{{EVIDENCE_BAR_CONTRADICTION_MARGINAL_VALUE_AND_BUDGET_RULES}}`
- Host capability: `{{managed-web-research status, read-only boundary, shell-network=false, and live verification evidence or unavailable reason}}`

Required research that is decision-critical must be `satisfied` before this
contract can be approved. If managed search is unavailable or insufficient,
record the limitation and return `BLOCKED`; recommended research may continue
only with explicit uncertainty and risk. WORK must return to PLAN when missing
external evidence would change this contract.

## Non-goals

- {{EXPLICITLY_EXCLUDED_WORK}}

## Assumptions

- {{USER_VISIBLE_OR_IMPLEMENTATION_ASSUMPTION}}

## Worktree baseline

- Branch or detached state: `{{BRANCH_STATE}}`
- Existing uncommitted paths: {{PATHS_OR_NONE}}
- Existing changes to preserve: {{PATHS_AND_CONSTRAINTS_OR_NONE}}

## Version control

- Version-control system: `{{GIT_OR_NONE}}`
- Baseline: `{{GIT_ROOT_BRANCH_OR_DETACHED_REVISION_INDEX_STAGED_STATE_OR_NOT_APPLICABLE}}`
- Logical commit boundary: `{{ONE_LOGICAL_CHANGE_AND_EXACT_PATHS_OR_NOT_APPLICABLE}}`
- Changelog decision: `{{REQUIRED_NOT_REQUIRED_OR_NOT_APPLICABLE}}`
- Changelog file: `{{PATH_OR_NOT_APPLICABLE}}`
- Changelog category: `{{ADDED_CHANGED_DEPRECATED_REMOVED_FIXED_SECURITY_OR_NOT_APPLICABLE}}`
- Changelog entry: `{{USER_FACING_ENTRY_OR_POLICY_REASON_OR_NOT_APPLICABLE}}`
- Proposed Conventional Commit message: `{{MESSAGE_OR_NOT_APPLICABLE}}`
- Commit authority: `none`
- Push authority: `none`
- Push target: `not-applicable`

`none` is the safe default for both authorities. Replace commit authority only with exact user approval for this logical boundary. Replace push authority only with separate exact user approval and set the remote and refspec in Push target. Approval of this contract or implementation does not imply either authority.

## Documentation

- Documentation impact: `{{CREATE_UPDATE_OR_NOT_REQUIRED}}`
- Policy reason: `{{CANONICAL_DOCUMENTATION_POLICY_REASON}}`
- Canonical feature document: `{{REPOSITORY_RELATIVE_PATH_OR_NOT_APPLICABLE}}`
- Feature index: `{{REPOSITORY_RELATIVE_PATH_OR_NOT_APPLICABLE}}`
- Code entry points: `{{PATHS_AND_STABLE_SYMBOLS_OR_NOT_APPLICABLE}}`
- Test entry points: `{{PATHS_AND_TEST_TARGETS_OR_NOT_APPLICABLE}}`
- Required sections: `{{SECTIONS_OR_NOT_APPLICABLE}}`
- Validation obligations: `{{LINK_PATH_SYMBOL_CONTENT_AND_FRESHNESS_CHECKS_OR_NOT_APPLICABLE}}`

Use exactly `create`, `update`, or `not-required`. For `create` and `update`, every path and validation field is implementation authority and must be completed atomically with code, tests, necessary Changelog, and configuration. For `not-required`, record a stable policy reason and use explicit `not-applicable` values rather than leaving fields unresolved.

## Allowed paths

- `{{PATH_OR_DIRECTORY}}`

## Forbidden paths

- `{{PATH_OR_DIRECTORY_OR_NONE}}`

## Constraints

- {{COMPATIBILITY_STYLE_SECURITY_PERFORMANCE_OR_DEPENDENCY_CONSTRAINT}}

## Applicable coding rules

- `{{CODING_RULE_COMPONENT_PATH_OR_NONE}}`

List every bundled coding-rule component document the worker must load before its first edit, one host-resolvable absolute path per entry, or `None`. Changing this list requires a new revision.

## Acceptance criteria

- AC-01: {{TESTABLE_OUTCOME}} (covers R-01)

## Verification

- `{{COMMAND}}` — {{EXPECTED_RESULT}}

## Dependency policy

{{NO_NEW_DEPENDENCIES_OR_EXACT_APPROVED_CHANGE}}

## Destructive and external actions

{{NONE_OR_EXACT_USER_AUTHORIZATION}}

## Block on

- A decision would change user-visible behavior, architecture, compatibility, dependencies, scope, allowed paths, data, or destructive-operation authority.
- Required permissions, tools, or external services are unavailable.
- Existing user changes overlap the approved write scope without explicit authorization.
- Acceptance criteria conflict or cannot be verified as written.
- Required feature documentation cannot be made accurate within the approved paths or validation obligations.
