# Build, acquisition, and verification

## Toolchain

Generated projects target Windows x64, Visual Studio 2022, C++23, CMake 3.25
or newer, and vcpkg in manifest mode. Set `VCPKG_ROOT` before configuring.
SKSE and the runtime-specific Address Library are end-user requirements outside
this source package.

The generated project does not pin an exact Visual C++ patch version. It lets
the selected VS2022 installation and vcpkg triplet resolve a compatible v143
toolset. First-party diagnostics are private target options, including
`/W4 /WX`; there is no global compiler-flags cache value and no mutation of
CommonLib's target.

## CommonLib acquisition

Default scaffolding is offline and prints the manual commands. `--git-init`
runs only local repository initialization. To acquire CommonLib explicitly:

```powershell
git init
git submodule add -b ng https://github.com/alandtse/CommonLibSSE-NG.git ext/CommonLibSSE
git submodule update --init --recursive
```

The add command creates a real `.gitmodules` and gitlink; commit both. The
separately named `--add-commonlib-submodule` option runs the first two commands
and is network-capable.

For an existing local source tree, set `COMMONLIBSSE_SOURCE_DIR` as a CMake cache
variable or environment variable. The path must contain CommonLib's
`CMakeLists.txt`. No legacy implementation fallback exists.

## Preset build

`CMakePresets.json` contains a hidden Visual Studio 2022 x64 `msvc` configure
base plus matching public Debug and Release configure/build presets:

```powershell
cmake --preset "msvc debug"
cmake --build --preset "msvc debug"
cmake --preset "msvc release"
cmake --build --preset "msvc release"
cpack --config "build/msvc release/CPackConfig.cmake"
```

Each build preset references the same-named configure preset and maps explicitly
to Debug or Release for the Visual Studio multi-config generator. Expected
release DLL output is below `build/msvc release/src/Release/`. Packaging
installs the DLL under `SKSE/Plugins` and the PDB at package root.

`COPY_OUTPUT` is off by default. To enable it, set `COMPILED_PLUGINS_PATH` and
configure with `-DCOPY_OUTPUT=ON`. This is an explicit local deployment write,
not part of source-package maintenance.

## Dependency lock

The default baseline
`ee12231b20c95013c6638d845d04c91559a1d1ff` and versioned dependency entries
mirror CommonLibSSE-NG v6.7.0 branch `ng` on 2026-08-25. CommonLib currently
requires vcpkg-cmake-config, DirectXMath, DirectXTK, fmt, nlohmann-json,
rapidcsv, SimpleIni, spdlog, toml11, and xbyak. DirectXTK and SimpleIni remain
in minimal manifests because they are current CommonLib requirements, even
though the generated first-party target only finds/links them directly when a
selected feature uses them.

Do not update the submodule independently. Compare CommonLib's manifest, CMake
helper, runtime defaults, nested content, and license files, then update the
baseline, versions, runtime references, and license details together.

## External coding-rule authority

The generated project uses the installed
`lightweight-coding-workflow` skill's `assets/coding-rules/`
directory and its `manifest.json` as the canonical rule source.
Locate that skill through the host's skill-discovery mechanism and resolve
the rule paths inside its root; do not assume a relative sibling path and do
not fall back to guessing. A separately copied SKSE rule set, fallback,
symlink, or second hash inventory is not allowed. When the
lightweight-coding-workflow skill is not installed, treat the rule authority
as unavailable and record scaffolding or maintenance work as blocked on that
missing dependency rather than proceeding without it.

Update the rules only in the lightweight source through a separately approved
change. Keep the shared code contract, applicable C++ references, manifest
entries, and this direct dependency aligned; do not cache hashes or copy rule
files into the SKSE package.

## Generated-project inspection

When CMake is installed, list presets without configuring dependencies:

```powershell
cmake --list-presets
cmake --build --list-presets
```

Both outputs must expose `msvc debug` and `msvc release`. When
`C:/env/vcpkg/vcpkg.exe` exists, copy a generated `vcpkg.json` to an isolated
temporary fixture and run:

```powershell
C:/env/vcpkg/vcpkg.exe format-manifest <temporary-vcpkg.json>
```

Formatting changes must remain in the temporary fixture.

## Version 0.3 migration

Existing generated projects must move the CommonLib gitlink from
`extern/CommonLibSSE` to `ext/CommonLibSSE`, rename `CompiledPluginsPath` to
`COMPILED_PLUGINS_PATH`, and rename `CommonLibSSEPath_NG` to
`COMMONLIBSSE_SOURCE_DIR`. Regenerate or migrate first-party declarations into
the normalized project root namespace and lowercase module namespaces. CMake
3.25 is now the minimum, and local workflows may use both `msvc debug` and the
unchanged `msvc release` commands.

## External build and runtime verification

A release claim additionally requires a real CommonLib checkout, installed
vcpkg dependencies, Windows SDK/MSVC, SKSE, and at least one selected Skyrim
runtime. Verify configure, build, package contents, plugin/SKSE logs, Load/data
messages, and selected hooks. Expand across SE/AE/VR whenever runtime-sensitive
code changes.

Template inspection alone does not prove a DLL links or runs in Skyrim. Record
unavailable compiler, SDK, submodule, vcpkg, game, and Address Library checks as
unverified rather than success.

## Licensing check

Generated `README.md`, `LICENSE`, and VERSIONINFO must all state
GPL-3.0-or-later. CommonLibSSE-NG's own Modding Exception and GPL-3.0 Linking
Exception (with Corresponding Source) remain upstream terms. Before distributing
a statically linked DLL, review the exact exception and corresponding-source
requirements at the pinned CommonLib revision.
