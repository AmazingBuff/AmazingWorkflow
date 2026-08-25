---
task_id: "{{TASK_ID}}"
revision: {{REVISION}}
status: "APPROVED"
created_at: "{{ISO_8601_TIMESTAMP}}"
supersedes: null
protocol_version: "0.5"
host_adapter: "{{VERIFIED_HOST_ADAPTER_ID}}"
adapter_version: "{{VERIFIED_ADAPTER_VERSION}}"
implementation_model: "{{USER_APPROVED_MODEL_OR_INHERIT_PARENT}}"
reasoning_effort: "{{USER_APPROVED_EFFORT_OR_DEFAULT}}"
approved_at: "{{ISO_8601_TIMESTAMP}}"
approval_summary: "{{USER_APPROVAL_SUMMARY}}"
repository_root: "{{ABSOLUTE_REPOSITORY_ROOT}}"
baseline_revision: "{{GIT_REVISION_OR_NOT_APPLICABLE}}"
---

# Implementation Contract: {{TASK_TITLE}}

## Objective

{{ONE_VERIFIABLE_OBJECTIVE}}

## Requirements

- R-01: {{REQUIRED_BEHAVIOR}}

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
