# Generated project structure

## File ownership

```text
<Project>/
├── .gitignore
├── CMakeLists.txt
├── CMakePresets.json
├── LICENSE
├── README.md
├── vcpkg.json
├── cmake/
│   ├── Plugin.h.in
│   ├── packaging.cmake
│   └── version.rc.in
├── extern/
│   └── CommonLibSSE/       # only after a real git submodule add
└── src/
    ├── CMakeLists.txt
    ├── main.cpp
    ├── pch.h
    └── selected feature pairs
```

The generator never writes `.gitmodules`. Git creates that file together with
the `extern/CommonLibSSE` gitlink only after:

```powershell
git submodule add -b ng https://github.com/alandtse/CommonLibSSE-NG.git extern/CommonLibSSE
```

## Build composition

The root `CMakeLists.txt` owns project metadata, `COPY_OUTPUT`, the three
`ENABLE_SKYRIM_*` runtime options, `BUILD_TESTS=OFF`, CommonLib source
discovery, and subdirectory order. Runtime options are set before CommonLib is
added. CommonLib comes from `extern/CommonLibSSE` or an explicit
`CommonLibSSEPath_NG` source directory; no second implementation is accepted.

`src/CMakeLists.txt` owns explicit first-party sources, generated
`Plugin.h`/VERSIONINFO resources, feature packages, and the plugin target. It
uses:

```cmake
add_commonlibsse_plugin(
    ${PROJECT_NAME}
    AUTHOR "${PROJECT_AUTHOR}"
    USE_ADDRESS_LIBRARY
    SOURCES ${HEADER_FILES} ${SOURCE_FILES}
)
```

CommonLib generates Query/version metadata and links its target. The project
adds only direct first-party dependencies and private compile policies. `/W4`
and `/WX` are target-scoped; the generated project never modifies CommonLib's
warning options.

## Lifecycle composition

`main.cpp` initializes logging, calls `SKSE::Init`, registers one message
listener, runs selected Load glue, and returns. Data-loaded glue installs the
Present hook. It does not contain a fixed runtime floor or a hand-written
compatibility list.

Feature ownership:

| Feature | Files | Lifecycle/dependencies |
| --- | --- | --- |
| `config` | `config.h/.cpp` | `Config::load()` during Load; SimpleIni |
| `present_hook` | `esp_renderer.h/.cpp` | `ESPRenderer::install()` at data loaded; DirectXTK |
| `hotkey` | `input.h/.cpp` | requires config + Present; `Input::poll()` every Present |
| `vtable_hook` | `hooks.h/.cpp` | `Hooks::install()` during Load |
| `event_sink` | `hit_events.h/.cpp` | static sink installed during Load |

Every accepted feature has its files, source registration, includes, direct
links, and reachable lifecycle call. Feature ordering is canonical regardless
of CLI order, so repeated inputs produce stable output.

## Rendering ownership

The Present module holds only device-bound helper resources across frames. A
device change resets and recreates the deferred context, CommonStates, effect,
and PrimitiveBatch. Each Present obtains local ComPtr references to the swap
chain device, back buffer, render-target view, command list, and immediate
context. Rendering is recorded on the deferred context, finished into a command
list, cleared, and executed with the restore-state flag set. All per-frame
references are destroyed before the original Present function is called.

## Generated manifest

The generated `vcpkg.json` uses a normalized lowercase hyphenated package name
and a 40-hex baseline. Its dependency set mirrors CommonLibSSE-NG v6.7.0 on
2026-08-25. The set is intentionally not inferred feature by feature because
current CommonLib itself requires DirectXMath, DirectXTK, SimpleIni, and the
other listed ports. A CommonLib update is one coordinated manifest/baseline/
runtime/license change, never an isolated submodule bump.
