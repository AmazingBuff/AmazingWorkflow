# Changelog

## [0.2] - 2026-08-25

### Added

- Add deterministic standard-library scaffold tests, package validation, and a
  hashed provenance manifest for every bundled coding-rule file.
- Add an explicit network-capable CommonLibSSE-NG submodule option while
  keeping default generation and `--git-init` local-only.

### Changed

- Change generated projects to CommonLibSSE-NG branch `ng`, its 2026-08-25
  vcpkg baseline/dependency requirements, official plugin metadata generation,
  matching configure/build presets, and GPL-3.0-or-later output.
- Change Present rendering to per-frame back-buffer/view ownership, device-aware
  helper recreation, deferred command recording, and complete immediate-context
  state restoration.

### Removed

- Remove the fabricated `.gitmodules`, legacy CommonLib implementation path,
  global compiler flags, exact MSVC patch-toolset pin, hand-written runtime
  metadata, fixed AE minimum, and unused generated helpers.

### Fixed

- Fix generated SKSE projects, add deterministic scaffold validation, and align
  CommonLib, Git, runtime, build, and licensing behavior.
- Fix hotkey dependency wiring, malformed placeholder detection, unsafe CLI
  metadata handling, warning-clean event sinks, and stale static-sink examples.
- Prevent documented validation commands from leaving Python bytecode caches
  and reject any cache artifacts present in the package.
- Put copyright ownership and the GPL SPDX identifier in their correct Windows
  VERSIONINFO fields.

## [0.1] - 2026-08-23

### Added

- Initial host-neutral port of the SKSE plugin template skill from its DeepSeek
  Harness deployment into a standalone source suite.
- Vendor the coding-standard components (`small-project-code-contract`,
  `small-project-cpp-rules`) adapted from the small-project workflow so the
  suite is self-contained on any agent.
- Align all templates and generated output with the bundled C++/CMake rules:
  file-header comments with scaffold-injected dates, 4-space indentation,
  naming fixes (`g_` namespace-scope state, `Upper_Snake_Case` constants),
  static sink instead of bare `new`, corrected logger sink declaration,
  `msvc release` preset naming with platform condition, and removal of local
  formatter configs in favor of the bundled rules.
