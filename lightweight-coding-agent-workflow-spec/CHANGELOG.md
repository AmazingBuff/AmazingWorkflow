# Changelog

## [Unreleased]

## [0.5] - 2026-08-25

### Added

- Add the canonical Feature Documentation Convention, reusable feature-document template, package feature index, and canonical package feature document.
- Add Documentation Impact fields to proposals and contracts plus `DOCUMENTATION` evidence to every implementation result state.
- Add a deterministic standard-library package validator and fixture-based unit tests for version, link, adapter, placeholder, documentation, manifest, metadata, and source/install drift.
- Add a sorted coding-rule integrity manifest with SHA-256, per-file provenance, and synchronization notes.

### Changed

- Change the Core, Adapter Contract, contract asset, Codex adapter, DSH adapter, template, feature documentation, and package guidance to protocol `0.5`.
- Change implementation dispatch eligibility so only compatible `VERIFIED` adapters can cross the product-write gate.
- Change the Codex adapter to version `0.5`, retain its nine capabilities, and document current explicit/default/parent model resolution while keeping the custom Agent model-neutral.
- Change feature-document and index maintenance to share the implementation's logical Git boundary with tests, necessary Changelog, configuration, and validation.
- Change installation guidance to distinguish the currently used user-level `.codex` deployment from portable `.agents/skills` authoring/discovery locations and add executable source/install parity validation.

### Fixed

- Fix inconsistent current-version declarations and the obsolete compatibility range that paired the current Core with older adapter metadata.
- Fix the DSH candidate mapping so its `EXPERIMENTAL` state is explicitly non-dispatchable before product writes.
- Fix bundled coding-rule integrity and provenance gaps without adding a runtime dependency on another workflow specification.
- Fix package-tree, support-matrix, validation, compatibility, and feature-navigation documentation to describe the files and behavior shipped together.

## [0.4] - 2026-08-22

### Added

- Added the bundled coding-rule component layer adapted from the small-project engineering standards.
- Added the DSH candidate adapter at `EXPERIMENTAL` with nine authored capability mappings and a promotion checklist.

### Changed

- Added the optional `Applicable coding rules` contract section and matching dispatch-envelope entries.

## [0.3] - 2026-08-21

### Added

- Added version-control planning and evidence for Git-backed coding tasks.
- Added Codex handling for read-only Git baselines, exact-path staging, bounded commits, and separately authorized pushes.

### Changed

- Made the Skill reference the canonical source for the Git commit and Changelog convention.
