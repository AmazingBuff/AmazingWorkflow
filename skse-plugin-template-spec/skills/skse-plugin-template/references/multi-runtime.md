# SE, AE, and VR runtime model

## One CommonLib implementation

Every generated project uses `alandtse/CommonLibSSE-NG` branch `ng` as the
single implementation for Skyrim SE, AE, and VR. The generator rejects any
other `--commonlib` value. A local source checkout is discovered at
`extern/CommonLibSSE` or through `CommonLibSSEPath_NG`.

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
CommonLib; document and test every supported branch.

## Official plugin metadata

The generated source target uses:

```cmake
add_commonlibsse_plugin(
    ${PROJECT_NAME}
    AUTHOR "${PROJECT_AUTHOR}"
    USE_ADDRESS_LIBRARY
    SOURCES ${HEADER_FILES} ${SOURCE_FILES}
)
```

CommonLibSSE-NG generates both historical discovery forms with the selected
runtime configuration, project version, name, author, struct independence, and
Address Library compatibility. First-party `main.cpp` therefore defines only
the Load entry point. It must not reintroduce a hard-coded minimum AE version or
a fixed latest-runtime list.

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
content to be initialized through the real recursive submodule update. Package
tests do not fetch that content or claim a VR DLL build. Code touching
runtime-dependent layouts must preserve CommonLib's multi-target abstractions.

## Update rule

Before moving CommonLib, review its runtime options, plugin CMake helper,
`vcpkg.json`, nested dependencies, and license files together. Update the
generated baseline/dependency list, docs, validator, and all runtime fixtures in
the same change.
