# Feature Documentation Convention

Status: canonical

Policy version: `0.5`

Feature documentation is maintained implementation material. It helps a human or future agent find a cohesive feature, understand its boundaries and invariants, verify it, and change it safely without turning the document into a line-by-line retelling of the code.

## Decision policy

Every coding proposal and approved implementation contract records one Documentation Impact decision and a policy reason:

| Decision | Use when | Required outcome |
| --- | --- | --- |
| `create` | A cohesive user-visible or developer-facing feature or module has no canonical feature document. | Create one canonical document and add it to the feature index. |
| `update` | Work changes an existing feature's behavior, architecture, interfaces, invariants, code navigation, failure modes, dependencies, tests, or safe modification guidance. | Update the existing canonical document and its index entry when navigation or identity changes. |
| `not-required` | The change is trivial and does not alter the durable understanding of a feature, such as formatting, a typo, a narrowly local comment, or a behavior-preserving internal edit whose code and tests remain navigable. | Record a specific, stable policy reason; do not use the absence of a document or schedule pressure as the reason. |

A bug fix is not automatically `not-required`. Use `update` when the fix changes a documented invariant, failure mode, interface, or modification rule. A new document is not required for every Issue, task, commit, small fix, or mechanical edit.

## Cohesive granularity and ownership

- One document owns one cohesive feature or module. Later tasks update it instead of creating ticket-specific duplicates.
- The canonical document lives with the repository that owns the implementation. When the repository has no established convention, use `docs/features/<feature-slug>.md` and index it from `docs/features/README.md`.
- Respect an established documentation structure when it already provides a clear canonical location and index. Record those paths in the implementation contract instead of also creating the default tree.
- The owning feature's implementation change owns documentation freshness. Documentation is not deferred to a third workflow phase or a separate documentation agent.

## Required contents

A canonical feature document must let a reader answer why the feature exists, where it lives, how it behaves, how it fails, how it is verified, and what must stay synchronized. Use the reusable [feature-document template](../assets/feature-document.md) and retain these subjects:

1. Purpose.
2. Scope and non-goals.
3. Architecture or data flow at the level needed to reason about the feature.
4. A code map with repository-relative paths and stable symbols or roles.
5. User-facing, developer-facing, or internal interfaces that constrain changes.
6. Invariants and compatibility rules.
7. Failure modes and expected handling.
8. Runtime, build, data, service, and policy dependencies, including an explicit statement when there are none.
9. Tests and verification entry points.
10. Safe modification guidance.
11. Files and artifacts that must remain synchronized.
12. Related history that explains durable decisions without duplicating a ticket log.

Sections may state that a subject is not applicable with a reason. Do not remove a required subject merely because the current implementation is small.

## Navigation rules

- Use repository-relative paths. Make document paths clickable with relative Markdown links when the target belongs in the repository.
- Name stable entry points such as exported types, commands, configuration keys, headings, targets, or test suites. Do not use ordinary line numbers as navigation anchors.
- Record both implementation and test or verification entry points. If a feature has no persistent automated test file, identify the real validation target and explain the bounded check that exercises it.
- Keep the canonical document reachable from the feature index, and link outward to deeper reference material rather than copying canonical policy into several files.
- Validate every listed path. Validate named symbols when the referenced artifact has symbols.

## Freshness and atomic maintenance

When the decision is `create` or `update`, maintain the canonical document and feature index atomically with the affected implementation, tests, necessary Changelog entry, and configuration in the same logical Git boundary. Before reporting completion:

- remove or correct stale paths, interfaces, invariants, failure behavior, and verification instructions;
- confirm synchronized-file guidance still covers every artifact that can drift together;
- report the document and index paths, navigation checks, validation results, and freshness status in `DOCUMENTATION` evidence.

If required documentation cannot be made accurate within the approved scope, the implementation is not complete. Return `BLOCKED` when new authority or a contract revision can resolve the gap, or `FAILED` when the approved task cannot progress in the current environment.

## Validation

Validation is proportional to the feature but always checks:

- the Documentation Impact decision and policy reason are present;
- required sections are substantive or carry an explicit not-applicable reason;
- the feature index reaches the canonical document;
- relative Markdown links resolve;
- repository-relative code, test, configuration, and document paths exist;
- named entry-point symbols exist when applicable;
- documented interfaces, invariants, failure modes, dependencies, and verification commands match the implementation;
- the result schema reports navigation, validation, and freshness evidence.

Validation may be performed by existing repository tools and bounded structural checks. This convention does not require a new runtime, dependency, documentation framework, or dedicated test harness.

When a workflow source package provides a deterministic package validator, its tests seed documentation-integration gaps and the validator checks the canonical document, feature index, contract fields, Core result schemas, adapter relay, Git boundary, links, paths, and required sections together. Installation of the Skill does not create a runtime dependency on that source validator.

## Code readability boundary

Feature documentation explains intent, boundaries, navigation, and safe change constraints. It must not compensate for unclear naming, oversized modules, hidden coupling, missing tests, or unreadable control flow. Keep code and tests understandable on their own; use the document to connect durable concepts that cannot be conveyed locally without duplication.
