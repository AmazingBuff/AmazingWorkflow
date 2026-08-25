# Build, acquisition, and verification

## Toolchain

Generated projects target Windows x64, Visual Studio 2022, C++23, CMake 3.22
or newer, and vcpkg in manifest mode. Set `VCPKG_ROOT` before configuring.
SKSE and the runtime-specific Address Library are end-user requirements, not
package-test inputs.

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
git submodule add -b ng https://github.com/alandtse/CommonLibSSE-NG.git extern/CommonLibSSE
git submodule update --init --recursive
```

The add command creates a real `.gitmodules` and gitlink; commit both. The
separately named `--add-commonlib-submodule` option runs the first two commands
and is network-capable. Tests replace its process boundary with a mock.

For an existing local source tree, set `CommonLibSSEPath_NG` as a CMake cache
variable or environment variable. The path must contain CommonLib's
`CMakeLists.txt`. No legacy implementation fallback exists.

## Preset build

`CMakePresets.json` contains a configure preset and a build preset with the
same public name:

```powershell
cmake --preset "msvc release"
cmake --build --preset "msvc release"
cpack --config "build/msvc release/CPackConfig.cmake"
```

The build preset references the configure preset and selects Release for the
Visual Studio multi-config generator. Expected DLL output is below
`build/msvc release/src/Release/`. Packaging installs the DLL under
`SKSE/Plugins` and the PDB at package root.

`COPY_OUTPUT` is off by default. To enable it, set `CompiledPluginsPath` and
configure with `-DCOPY_OUTPUT=ON`. This is an explicit local deployment write,
not part of package validation.

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
baseline, versions, docs, validator, and tests together.

## Offline package verification

From `skse-plugin-template-spec/`:

```powershell
python -B -m unittest discover -s tests -v
python -B tools/validate_package.py .
```

These standard-library checks generate isolated temporary fixtures, parse every
JSON file, scan exact/spaced placeholders, verify file and dependency sets,
exercise every runtime and representative metadata, mock Git success/failure,
and enforce Present resource/state invariants. The tests import the executable
Python modules, so a separate bytecode compilation command is unnecessary.
`-B` prevents cache creation, and validation rejects every present
`__pycache__` directory and `.pyc` file. No test invokes a network submodule,
downloads vcpkg ports, or needs game assets.

When CMake is installed, list presets without configuring dependencies:

```powershell
cmake --list-presets
cmake --build --list-presets
```

Both outputs must expose `msvc release`. When
`C:/env/vcpkg/vcpkg.exe` exists, copy a generated `vcpkg.json` to an isolated
temporary fixture and run:

```powershell
C:/env/vcpkg/vcpkg.exe format-manifest <temporary-vcpkg.json>
```

Formatting changes must remain in the temporary fixture.

## External build and runtime verification

A release claim additionally requires a real CommonLib checkout, installed
vcpkg dependencies, Windows SDK/MSVC, SKSE, and at least one selected Skyrim
runtime. Verify configure, build, package contents, plugin/SKSE logs, Load/data
messages, and selected hooks. Expand across SE/AE/VR whenever runtime-sensitive
code changes.

Package validation alone does not prove a DLL links or runs in Skyrim. Record
unavailable compiler, SDK, submodule, vcpkg, game, and Address Library checks as
unverified rather than success.

## Licensing check

Generated `README.md`, `LICENSE`, and VERSIONINFO must all state
GPL-3.0-or-later. CommonLibSSE-NG's own Modding Exception and GPL-3.0 Linking
Exception (with Corresponding Source) remain upstream terms. Before distributing
a statically linked DLL, review the exact exception and corresponding-source
requirements at the pinned CommonLib revision.
