# {{PROJECT_NAME}}

{{DESCRIPTION}}

This is version {{PROJECT_VERSION}} of a C++23 SKSE plugin generated for runtime
selection `{{RUNTIME_SELECTION}}` with features `{{FEATURE_SELECTION}}` and
CommonLibSSE-NG branch `ng`.

## Requirements

- Windows x64 and Visual Studio 2022 with Desktop development with C++.
- CMake 3.22 or newer.
- Git and vcpkg with `VCPKG_ROOT` set.
- The matching SKSE runtime and Address Library installation for SE, AE, or VR.

## Add CommonLibSSE-NG

The scaffold does not invent `.gitmodules` and performs no network operation by
default. From this project directory, initialize the real submodule explicitly:

```powershell
git init
git submodule add -b ng https://github.com/alandtse/CommonLibSSE-NG.git extern/CommonLibSSE
git submodule update --init --recursive
```

Commit both the generated `.gitmodules` file and the
`extern/CommonLibSSE` gitlink. A local checkout may instead be supplied through
the `CommonLibSSEPath_NG` CMake cache variable or environment variable.

## Build

```powershell
cmake --preset "msvc release"
cmake --build --preset "msvc release"
cpack --config "build/msvc release/CPackConfig.cmake"
```

The configure and build presets share the name `msvc release`; the build preset
links to the configure preset and selects Release. The DLL is produced below
`build/msvc release/src/Release/`. Set `CompiledPluginsPath` and configure with
`-DCOPY_OUTPUT=ON` only when an explicit local deployment copy is wanted.

CommonLibSSE-NG and vcpkg may acquire their own build dependencies during a real
configure. This repository pins the vcpkg baseline that matched CommonLibSSE-NG
v6.7.0 on 2026-08-25. Updating CommonLib requires a coordinated review of its
`vcpkg.json`, this project's baseline, dependency versions, runtime options, and
license obligations.

## Installation

Copy `{{PROJECT_NAME}}.dll` to `Data\SKSE\Plugins\`. The plugin log is written
under the active Skyrim documents directory as `SKSE\{{PROJECT_NAME}}.log`.

## License

Copyright is retained by {{AUTHOR}}. This generated project defaults to
GPL-3.0-or-later; see [LICENSE](LICENSE).

CommonLibSSE-NG is a separate dependency distributed under
GPL-3.0-or-later with its own Modding Exception and GPL-3.0 Linking Exception
(with Corresponding Source). Those upstream exceptions are not relicensed,
copied, or altered by this project. A plugin statically linked with
CommonLibSSE-NG must remain GPL-3.0-or-later or otherwise GPL-compatible and
must satisfy the upstream corresponding-source terms.
