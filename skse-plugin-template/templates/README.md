# {{PROJECT_NAME}}

{{DESCRIPTION}}

This is version {{PROJECT_VERSION}} of a C++23 SKSE plugin generated for runtime
selection `{{RUNTIME_SELECTION}}` with features `{{FEATURE_SELECTION}}` and
CommonLibSSE-NG branch `ng`.

First-party C++ is rooted at namespace `{{PROJECT_NAMESPACE}}`; feature modules
use lowercase namespaces such as `config`, `input`, and `esp_renderer`. The
global `SKSEPlugin_Load` export and framework override names remain external
ABI exceptions.

## Requirements

- Windows x64 and Visual Studio 2022 with Desktop development with C++.
- CMake 3.25 or newer.
- Git and vcpkg with `VCPKG_ROOT` set.
- The matching SKSE runtime and Address Library installation for SE, AE, or VR.

## Add CommonLibSSE-NG

The scaffold does not invent `.gitmodules` and performs no network operation by
default. From this project directory, initialize the real submodule explicitly:

```powershell
git init
git submodule add -b ng https://github.com/alandtse/CommonLibSSE-NG.git ext/CommonLibSSE
git submodule update --init --recursive
```

Commit both the generated `.gitmodules` file and the
`ext/CommonLibSSE` gitlink. A local checkout may instead be supplied through
the `COMMONLIBSSE_SOURCE_DIR` CMake cache variable or environment variable.

## Build

```powershell
cmake --preset "msvc debug"
cmake --build --preset "msvc debug"
cmake --preset "msvc release"
cmake --build --preset "msvc release"
cpack --config "build/msvc release/CPackConfig.cmake"
```

The Debug and Release configure/build presets inherit a hidden Visual Studio
2022 x64 base. Each build preset links to its same-named configure preset and
selects the corresponding configuration. The release DLL is produced below
`build/msvc release/src/Release/`. Set `COMPILED_PLUGINS_PATH` and configure
with `-DCOPY_OUTPUT=ON` only when an explicit local deployment copy is wanted.

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
