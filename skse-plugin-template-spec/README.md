# SKSE Plugin Template

Status: confirmed
Version: 0.2
Date: 2026-08-25

## Purpose

This host-neutral Skill package generates reproducible C++23 SKSE plugin
projects for Skyrim SE, AE, and VR. Every generated project uses
`alandtse/CommonLibSSE-NG` branch `ng`, official CommonLib plugin metadata,
target-scoped MSVC diagnostics, real configure/build presets, and a
GPL-3.0-or-later default.

## Scope and non-goals

The package scaffolds one plugin with optional INI configuration, Present-frame
hotkeys, a D3D11 Present overlay, a Character vtable hook, and a hit-event sink.
It validates package metadata and generated text before success is reported.

It does not install compilers, vcpkg, CommonLib, SKSE, game assets, or Address
Library data. It does not build against Skyrim in package tests, manage multiple
plugins, deploy files, or contact the network unless the caller explicitly uses
`--add-commonlib-submodule`. A legacy VR-only CommonLib fork is not supported.

## Architecture and data flow

```text
validated CLI values
        |
        v
scripts/scaffold.py ---- templates/ + selected feature templates
        |                         |
        +---- exact placeholder and JSON validation
                                  |
                                  v
                       generated CommonLibSSE-NG project

tools/validate_package.py ---- docs/templates/manifest/generated fixtures
        |
        v
deterministic standard-library test evidence
```

Runtime options are rendered in the generated root `CMakeLists.txt` before
CommonLib is added. The generated `src/CMakeLists.txt` then calls
`add_commonlibsse_plugin(...)`, which creates Query/version metadata, and links
only first-party feature requirements. `main.cpp` contains the Load entry point
and lifecycle glue.

## Code map

- [Skill index](skills/skse-plugin-template/SKILL.md) — usage and reference
  routing.
- [Generator](skills/skse-plugin-template/scripts/scaffold.py) — `main`,
  boundary validation, rendering, exact file-set checks, and Git setup.
- [Templates](skills/skse-plugin-template/templates/) — generated CMake, C++,
  manifest, README, license, resource, and optional feature sources.
- [Structure reference](skills/skse-plugin-template/references/structure.md) —
  generated file ownership and data flow.
- [Pattern reference](skills/skse-plugin-template/references/patterns.md) —
  warning-clean lifecycle and feature patterns.
- [Runtime reference](skills/skse-plugin-template/references/multi-runtime.md) —
  SE/AE/VR options and official metadata behavior.
- [Build reference](skills/skse-plugin-template/references/build-and-verify.md) —
  acquisition, presets, limitations, and checks.
- [Package validator](tools/validate_package.py) — `validate_package`,
  `validate_manifest`, links, templates, and generated-fixture invariants.
- [Generator tests](tests/test_scaffold.py) and
  [validator tests](tests/test_validate_package.py) — standard-library
  regression suite.

## CLI and generated interfaces

Run from `skills/skse-plugin-template/`:

```powershell
python scripts/scaffold.py --name My_Plugin --author "Your Name" --dir C:/work/My_Plugin
python scripts/scaffold.py --help
```

Key options:

- `--name` accepts a CMake/C++ identifier and derives a lowercase hyphenated
  vcpkg name (for example, `My_Plugin` becomes `my-plugin`).
- `--version` requires three numeric components, each no greater than 65535.
- `--baseline` requires exactly 40 hexadecimal characters.
- `--runtimes` accepts `all`, `se`, `ae`, `vr`, `se-ae`, `se-vr`, or
  `ae-vr`.
- `--features` accepts `config`, `present_hook`, `hotkey`, `vtable_hook`,
  and `event_sink`. `hotkey` requires both `config` and `present_hook` because
  Present is the frame source that invokes `Input::poll()`.
- `--commonlib` accepts only `ng`. Other values fail explicitly.
- `--git-init` runs local-only `git init` and never adds a submodule.
- `--add-commonlib-submodule` is explicitly network-capable: it initializes Git
  and runs exactly
  `git submodule add -b ng https://github.com/alandtse/CommonLibSSE-NG.git extern/CommonLibSSE`.

Default generation performs no Git or network subprocess. It emits the exact
manual command above and never fabricates `.gitmodules`. The real submodule
command creates `.gitmodules` and a gitlink; both must be committed by the
generated project's owner.

Names, authors, descriptions, versions, baselines, feature lists, paths, and
`SOURCE_DATE_EPOCH` are validated before rendering. Multiline/control metadata,
template delimiters, unsafe author quoting, unknown placeholders, and malformed
spaced placeholders fail without a success report. Quoted descriptions are
escaped separately for CMake while remaining readable in Markdown.

## Runtime, build, and license invariants

- `ENABLE_SKYRIM_SE`, `ENABLE_SKYRIM_AE`, and `ENABLE_SKYRIM_VR` are
  authoritative before CommonLib is added, and at least one is selected by
  every accepted runtime choice.
- `add_commonlibsse_plugin(...)` owns generated Query/version metadata with
  Address Library independence. Generated `main.cpp` contains no fixed AE
  minimum or fixed compatible-runtime list.
- Configure and build presets are both named `msvc release`, and the build
  preset references the configure preset. No global compiler-flag cache value
  or exact Visual C++ patch version is pinned.
- First-party MSVC warnings are target-scoped at `/W4 /WX`; third-party targets
  are not modified by the generated project.
- Present rendering records on a deferred context, executes the command list
  with immediate-context restoration, recreates helpers when the device changes,
  and releases per-frame back-buffer/RTV/command-list references before the
  original Present call.
- Generated code and resources default to GPL-3.0-or-later. CommonLibSSE-NG is
  separately GPL-3.0-or-later with its own Modding Exception and GPL-3.0 Linking
  Exception (with Corresponding Source). The template does not claim, copy, or
  alter those upstream exception terms.

## Failure modes

The generator returns nonzero with an actionable `error:` message for invalid
input, nonempty/symlink output directories, missing templates, unresolved
placeholders, invalid generated JSON, write failures, missing Git, and nonzero
Git commands. A failed requested Git action never proceeds to the scaffold
success summary. A failed network submodule add may leave generated files and a
local repository for inspection, but is still reported as failure.

Generated CMake fails clearly if neither `extern/CommonLibSSE` nor a valid
`CommonLibSSEPath_NG` source directory exists. Real configure/build can also
fail when Visual Studio, vcpkg packages, CommonLib nested sources, SKSE headers,
or Windows SDK components are unavailable; package tests intentionally do not
claim those external builds passed.

## Dependencies

The source Skill, generator, validator, and tests use Python 3.11+ and only the
standard library. Generated projects target Windows x64, Visual Studio 2022,
CMake 3.22+, C++23, vcpkg, SKSE, and CommonLibSSE-NG.

The default vcpkg baseline is
`ee12231b20c95013c6638d845d04c91559a1d1ff`. Its manifest mirrors
CommonLibSSE-NG v6.7.0 requirements as of 2026-08-25:
`vcpkg-cmake-config`, `directxmath`, `directxtk`, `fmt`,
`nlohmann-json`, `rapidcsv`, `simpleini`, `spdlog`, `toml11`, and
`xbyak` with the upstream minimum versions. Future CommonLib revisions require
a coordinated submodule, baseline, dependency, runtime, and license review.

## Tests

Run every offline check from this package root:

```powershell
python -B -m unittest discover -s tests -v
python -B tools/validate_package.py .
```

`-B` prevents Python from writing bytecode caches. The tests already import the
generator and validator entry points, and package validation rejects every
present `__pycache__` directory or `.pyc` file.

The suite covers minimal/all-feature scaffolds, every runtime, names and quoted
descriptions, invalid metadata, feature dependencies, exact placeholder
exhaustion, JSON/dependency/file sets, preset linkage, modern metadata, licensing,
warning-clean patterns, Present lifetime/state invariants, and mocked Git
subprocess success/failure. Manifest fixtures seed missing, extra, duplicate,
and changed bundled-rule cases. No test invokes a real submodule or needs game
assets.

When CMake is available, additionally generate a temporary fixture and run
`cmake --list-presets` plus `cmake --build --list-presets`. When
`C:/env/vcpkg/vcpkg.exe` exists, run `format-manifest` only on a temporary
generated manifest.

## Safe modification

Keep validation at the CLI boundary and add new feature files through the
single `FEATURES` table, canonical feature order, generated file-set assertion,
tests, and documentation together. Do not add a second CommonLib source or
hand-write plugin version metadata. Preserve deferred-context state isolation
if extending the overlay.

Before updating CommonLib, compare its `ng` branch `vcpkg.json`,
`cmake/CommonLibSSE.cmake`, license files, runtime options, and toolchain
requirements. Refresh the pinned baseline and tests atomically. Before changing
bundled coding rules, compare the recorded provenance, update only the intended
files, and refresh every hash in the integrity manifest.

## Synchronized files

Behavior changes must keep these files current as one logical unit:

- `README.md` and `CHANGELOG.md`.
- `skills/skse-plugin-template/SKILL.md`.
- Generated `templates/README.md`, `templates/LICENSE`, CMake/presets,
  vcpkg/resource metadata, core C++, and selected feature templates.
- All four files under `skills/skse-plugin-template/references/`.
- `assets/coding-rules/manifest.json`, `tools/validate_package.py`, and tests.

The package validator resolves Markdown links, verifies named entry points,
compares templates with generated fixtures, and enforces this synchronized
surface.

## Release history

Release 0.2 repairs placeholder validation, CommonLib metadata/dependencies,
Git acquisition, feature wiring, Present state isolation, presets, licensing,
tests, documentation, and bundled-rule integrity. See
[CHANGELOG.md](CHANGELOG.md) for the complete release record.
