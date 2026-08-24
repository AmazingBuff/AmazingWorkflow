# Changelog

## [Unreleased]

### Added

- Add the bundled coding-rule component layer (`assets/coding-rules/`) adapted from the small-project workflow standards, carried by the contract's new `Applicable coding rules` section.
- Add the DeepSeek Harness (`dsh`) host adapter at `EXPERIMENTAL` with nine capability mappings, explicit-acknowledgement selection, and a promotion verification checklist.
- Add version-control planning and evidence for Git-backed coding tasks.
- Add verified Codex handling for read-only Git baselines, exact-path staging, bounded commits, and separately authorized pushes.

### Changed

- Change the Core protocol to additive `0.4`: an optional `Applicable coding rules` contract section, matching dispatch-envelope entries, and explicit-user-acknowledged selection of one `EXPERIMENTAL` adapter; adapters verified under `0.3` remain eligible within the documented compatibility range.
- Change proposals, contracts, and completion reports to record Changelog disposition, a proposed Conventional Commit message, and separate commit and push authority.
- Change the Skill reference to be the canonical source for the Git commit and Changelog convention.
