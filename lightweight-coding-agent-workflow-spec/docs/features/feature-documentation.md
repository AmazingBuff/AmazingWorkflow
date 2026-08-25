# Feature documentation policy

Status: current

Canonical path: `docs/features/feature-documentation.md`

Last verified against: protocol `0.5`

## Purpose

The feature-documentation policy makes durable feature knowledge part of the two-phase coding workflow. It gives humans and future agents a canonical place to find a feature's purpose, boundaries, architecture, entry points, invariants, failure modes, verification, and safe modification guidance.

## Scope and non-goals

In scope:

- Classify each coding proposal as documentation `create`, `update`, or `not-required` with a policy reason.
- Freeze documentation paths, navigation targets, required sections, and validation obligations in the approved implementation contract.
- Maintain required feature documentation atomically with implementation and return structured `DOCUMENTATION` evidence.
- Provide a canonical policy, reusable template, default package location, and feature index.

Out of scope:

- Creating a document for every Issue, commit, trivial fix, formatting change, or behavior-preserving internal edit.
- Replacing readable code, modular design, meaningful names, or tests with prose.
- Adding a documentation agent, workflow phase, runtime, dependency, or external framework.
- Retroactively documenting every existing feature.

## Architecture

The [Planner Skill](../../skills/lightweight-coding-workflow/SKILL.md) loads the canonical [Feature Documentation Convention](../../skills/lightweight-coding-workflow/references/feature-documentation-convention.md), classifies Documentation Impact, and records the decision in a contract created from the [implementation-contract asset](../../skills/lightweight-coding-workflow/assets/implementation-contract.md). The implementation worker maintains the canonical feature document and index inside the same logical change as affected implementation, tests, configuration, and Changelog. The host-neutral [Core Protocol](../../skills/lightweight-coding-workflow/references/protocol.md) carries documentation evidence through `DONE`, `BLOCKED`, and `FAILED`; adapters relay that evidence without adding a tenth capability, and only a `VERIFIED` adapter may dispatch product writes.

The [feature-document asset](../../skills/lightweight-coding-workflow/assets/feature-document.md) supplies the required document shape. A repository may use an established documentation structure instead of the defaults, but the contract records the chosen canonical paths. The [package validator](../../tools/validate_package.py) and its [unit tests](../../tests/test_validate_package.py) enforce the package-wide links among planning, contracts, implementation, result relay, Git boundaries, navigation, and freshness.

## Code map

| Repository-relative path | Stable symbol or entry point | Responsibility |
| --- | --- | --- |
| [skills/lightweight-coding-workflow/SKILL.md](../../skills/lightweight-coding-workflow/SKILL.md) | `Prepare the proposal`, `Approval gate and contract`, `Handle the result`, `Completion` | Planner classification, approval, dispatch, and completion reporting. |
| [skills/lightweight-coding-workflow/references/feature-documentation-convention.md](../../skills/lightweight-coding-workflow/references/feature-documentation-convention.md) | `Decision policy`, `Required contents`, `Navigation rules`, `Freshness and atomic maintenance`, `Validation` | Canonical create/update/not-required and document-quality policy. |
| [skills/lightweight-coding-workflow/references/protocol.md](../../skills/lightweight-coding-workflow/references/protocol.md) | `Required contract properties`, `Implementation rules`, `Result protocol`, `Planner completion report` | Host-neutral contract, implementation, and `DOCUMENTATION` result requirements. |
| [skills/lightweight-coding-workflow/assets/implementation-contract.md](../../skills/lightweight-coding-workflow/assets/implementation-contract.md) | `Documentation` | Frozen documentation decision, paths, entry points, sections, and validation obligations. |
| [skills/lightweight-coding-workflow/assets/feature-document.md](../../skills/lightweight-coding-workflow/assets/feature-document.md) | `Purpose`, `Code map`, `Tests and verification`, `Safe modification guidance`, `Synchronized files` | Reusable canonical feature-document structure. |
| [docs/features/README.md](README.md) | `Feature documentation` | Package feature index and discovery point. |
| [tools/validate_package.py](../../tools/validate_package.py) | `validate_package`, `_check_feature_documentation` | Deterministic package, integration, link, metadata, manifest, and install validation. |
| [tests/test_validate_package.py](../../tests/test_validate_package.py) | `PackageValidatorTests` | Isolated fixtures that prove documentation and other drift are detected. |

## Interfaces

- Planner proposals expose Documentation Impact as exactly `create`, `update`, or `not-required`, plus the policy reason and all applicable paths and validation obligations.
- Approved contracts preserve the documentation decision as immutable implementation authority; changing it materially requires a new revision.
- Implementation results expose a `DOCUMENTATION` section with decision, document and index paths, navigation evidence, validation evidence, and freshness status.
- Default paths are `docs/features/<feature-slug>.md` and `docs/features/README.md` only when the target repository has no established equivalent.
- The package validator exposes a standard-library Python CLI; `--installed-skill` and `--installed-agent` optionally compare the authoritative source with a deployed Codex copy.

## Invariants

- One canonical document represents one cohesive feature or module; tasks update it instead of creating ticket-specific duplicates.
- Documentation required by policy is part of implementation acceptance and the same logical Git boundary as affected code, tests, necessary Changelog, and configuration.
- Repository-relative paths and stable symbols provide navigation; ordinary line numbers do not.
- The Core remains host-neutral, and the Adapter Contract retains exactly nine capabilities.
- Only `VERIFIED` adapters may dispatch product writes; documentation evidence never relaxes the write gate.
- Documentation does not excuse unclear code or missing tests.

## Failure modes

| Failure | Expected handling | Verification |
| --- | --- | --- |
| Documentation Impact is absent or uses an unsupported value. | Stop before approval or revise the proposal and contract. | Inspect `Prepare the proposal` and the contract `Documentation` section. |
| A required document or index is stale, unreachable, or outside approved paths. | Repair within the approved scope; otherwise return `BLOCKED` for revised authority. | Resolve links, paths, and stable symbols listed in this document and the task contract. |
| Documentation is used to describe around unreadable code or missing tests. | Improve the implementation and tests within scope; prose alone cannot satisfy acceptance. | Review the changed code and run the contract's real verification entry points. |
| An adapter drops documentation evidence or adds a documentation capability. | Reject the mapping until lossless relay is restored while retaining nine capabilities. | Parse adapter metadata and inspect `relay_result`. |
| The package validator or installed copy drifts from the documented integration. | Fail deterministically with a categorized finding; update source, tests, docs, and manifest atomically when applicable. | Run the source validator and optional source/install comparison. |

## Dependencies

- No workflow runtime, package, service, database, network access, or external documentation framework is required.
- Source-package validation uses only Python standard-library modules and is not an installed-Skill runtime dependency.
- The policy depends on Markdown resources loaded by the Skill and on the target repository's real implementation/test entry points.

## Tests and verification

- [tools/validate_package.py](../../tools/validate_package.py) — run `python -B tools/validate_package.py --package .`; expect exit `0` and a protocol `0.5` success summary.
- [tests/test_validate_package.py](../../tests/test_validate_package.py) — run `python -B -m unittest discover -s tests -p "test_*.py"`; expect every isolated drift fixture to pass.
- [skills/lightweight-coding-workflow/references/adapters/codex.md](../../skills/lightweight-coding-workflow/references/adapters/codex.md) — validator parses front matter and verifies `support_state: VERIFIED`, protocol and adapter version `0.5`, exactly nine capabilities, and all nine operation sections.
- [docs/features/README.md](README.md) — validator resolves the index link to this canonical document.
- [docs/features/feature-documentation.md](feature-documentation.md) — validator resolves every relative Markdown link and confirms each required heading and package entry point.
- [skills/lightweight-coding-workflow/assets/feature-document.md](../../skills/lightweight-coding-workflow/assets/feature-document.md) — validator confirms every required section and confines placeholders to the intended template.

## Safe modification guidance

1. Start with the canonical convention when changing decision rules or document quality; keep summarized routing in the Skill and avoid copying the full policy elsewhere.
2. Update the contract asset and Core result schemas together when documentation evidence changes.
3. Update both adapter references without changing the nine-capability interface when relay or verification wording changes.
4. Keep this document, the feature index, README, DESIGN, Git convention, and Changelog synchronized with user-visible policy changes.
5. Re-run unit tests, source validation, and—after an authorized install—the source/install comparison before completion.

## Synchronized files

| Path | Why it must stay synchronized |
| --- | --- |
| [skills/lightweight-coding-workflow/SKILL.md](../../skills/lightweight-coding-workflow/SKILL.md) | Planner gates and completion reporting must match the canonical policy. |
| [skills/lightweight-coding-workflow/references/protocol.md](../../skills/lightweight-coding-workflow/references/protocol.md) | Contract and result obligations must carry the same evidence. |
| [skills/lightweight-coding-workflow/references/adapter-contract.md](../../skills/lightweight-coding-workflow/references/adapter-contract.md) | Adapter relay and verification must preserve documentation evidence without a new capability. |
| [skills/lightweight-coding-workflow/references/adapters/codex.md](../../skills/lightweight-coding-workflow/references/adapters/codex.md) | The verified mapping must dispatch and relay protocol `0.5` results. |
| [skills/lightweight-coding-workflow/references/adapters/dsh.md](../../skills/lightweight-coding-workflow/references/adapters/dsh.md) | The experimental mapping must remain non-dispatchable while documenting relay obligations. |
| [skills/lightweight-coding-workflow/references/adapters/template.md](../../skills/lightweight-coding-workflow/references/adapters/template.md) | Future mappings must include documentation-aware relay and verification. |
| [skills/lightweight-coding-workflow/assets/implementation-contract.md](../../skills/lightweight-coding-workflow/assets/implementation-contract.md) | Approved tasks must freeze the decision and validation obligations. |
| [skills/lightweight-coding-workflow/assets/feature-document.md](../../skills/lightweight-coding-workflow/assets/feature-document.md) | Generated feature documents must cover the canonical required contents. |
| [skills/lightweight-coding-workflow/references/git-commit-convention.md](../../skills/lightweight-coding-workflow/references/git-commit-convention.md) | Required documents and index changes must share the implementation's logical commit boundary. |
| [tools/validate_package.py](../../tools/validate_package.py) and [tests/test_validate_package.py](../../tests/test_validate_package.py) | Deterministic checks and seeded fixtures must match the integration contract. |
| [README.md](../../README.md), [DESIGN.md](../../DESIGN.md), and [CHANGELOG.md](../../CHANGELOG.md) | Package discovery, architecture, compatibility, and user-facing history must reflect protocol `0.5`. |

## Related history

- Protocol `0.3` introduced bounded Git planning and evidence; protocol `0.4` added bundled coding-rule components; the feature-documentation draft built on that logical-boundary model and ships in protocol `0.5`.
- Protocol `0.5` releases feature documentation with a verified-only write gate, manifest integrity, and deterministic source/install validation.
- See the package [Changelog](../../CHANGELOG.md) for the user-facing additions and changes.
