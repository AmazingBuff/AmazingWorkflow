# SE, AE, and VR runtime model

## Skyrim research checks

The `skse-plugin-template` binding makes the lightweight workflow's External
Research Gate mandatory for runtime-sensitive architecture. Before approving
CommonLib/SKSE APIs, ABI/layout-sensitive code, relocation or vtable hooks,
rendering/Present, event/input/serialization/Papyrus integration, dependencies,
or copied third-party designs, record target runtime(s), CommonLib branch and
version, maintenance status, license/reuse status, and the implementation
differences found in authoritative upstream and maintained implementation
evidence. A single-source exception must be explained. Missing or conflicting
evidence returns the proposal to PLAN; it does not authorize a guessed
SE/AE/VR design.

## One CommonLib implementation

Every generated project uses `alandtse/CommonLibSSE-NG` branch `ng` as the
single implementation for Skyrim SE, AE, and VR. The generator rejects any
other `--commonlib` value. A local source checkout is discovered at
`ext/CommonLibSSE` or through the uppercase `COMMONLIBSSE_SOURCE_DIR` cache or
environment variable.

## Authoritative build options

The runtime choice maps to root CMake options before CommonLib is added:

| CLI value | SE | AE | VR |
| --- | --- | --- | --- |
| `all` | ON | ON | ON |
| `se` | ON | OFF | OFF |
| `ae` | OFF | ON | OFF |
| `vr` | OFF | OFF | ON |
| `se-ae` | ON | ON | OFF |
| `se-vr` | ON | OFF | ON |
| `ae-vr` | OFF | ON | ON |

CommonLib validates that at least one option is enabled and publishes the
matching ABI/runtime definitions. First-party code must use CommonLib
`RE::`/`REL::` abstractions and runtime probes for layout differences.

## Address resolution

Use Address Library identifiers and relocation wrappers:

```cpp
REL::Relocation<std::uintptr_t> character_vtable{ RE::VTABLE_Character[0] };
```

Do not embed SE-only, AE-only, or VR-only raw addresses. For a new engine call,
prefer an existing CommonLib wrapper. When a type or virtual function differs
by runtime, use the runtime-aware API and compile definitions supplied by
CommonLib; document every supported branch and keep runtime-specific checks
close to the affected code.

## Official plugin metadata

The generated source target uses:

```cmake
add_commonlibsse_plugin(
    ${PROJECT_NAME}
    AUTHOR "${PROJECT_AUTHOR}"
    USE_ADDRESS_LIBRARY
    SOURCES ${header_files} ${source_files}
)
```

CommonLibSSE-NG generates both historical discovery forms with the selected
runtime configuration, project version, name, author, struct independence, and
Address Library compatibility. First-party `main.cpp` therefore defines only
the Load entry point. It must not reintroduce a hard-coded minimum AE version or
a fixed latest-runtime list.

`SKSEPlugin_Load` remains a global C ABI export, and framework overrides such
as `ProcessEvent` retain their required spelling. All other first-party code is
placed under the normalized project root namespace and lowercase modules;
renaming external ABI identifiers for stylistic consistency is forbidden.

## Runtime lifecycle

- Load: reset the CommonLib module workaround, initialize logging and SKSE,
  register the message listener, load config, and install Load-time hooks/sinks.
- Data loaded: install renderer-dependent hooks after game data and the renderer
  are available.
- Present: poll an enabled hotkey and record the optional overlay through a
  deferred D3D11 context.
- New game/post-load: placeholders currently log lifecycle events; add project
  behavior only when required.

## VR constraints

VR support uses the same `ng` source and requires CommonLib's nested OpenVR
content to be initialized through the real recursive submodule update. Code
touching runtime-dependent layouts must preserve CommonLib's multi-target
abstractions.

## Update rule

Before moving CommonLib, review its runtime options, plugin CMake helper,
`vcpkg.json`, nested dependencies, and license files together. Update the
generated baseline/dependency list and the focused runtime/build references in
the same change.
