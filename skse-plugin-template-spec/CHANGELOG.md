# Changelog

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
