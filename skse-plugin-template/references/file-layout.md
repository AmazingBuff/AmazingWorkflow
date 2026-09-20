# File layout: responsibility first, then directories

Follow the reference project's pattern of "root build file + cmake generated
material + src grouped by responsibility". The reference directory names are
examples, not directories every plugin must have.

## Minimal project

main.cpp only handles the entry point, logging, and necessary initialization.
pch.h holds stable, widely used base headers and includes the build-generated
plugin.h. Metadata comes from the root CMake's PROJECT_NAME, PROJECT_VERSION,
PROJECT_NAMESPACE, and PROJECT_AUTHOR; do not copy project name/version
strings across modules.

A module's own header should express the callable interface; the cpp keeps the
implementation and private state. Project code lives inside
PLUGIN_NAMESPACE_BEGIN/END; SKSE exports keep the global C ABI.

## When to add files

| Actual need | Suggested location | Boundary |
| --- | --- | --- |
| Persisted settings | src/config/config.h/.cpp | Only this plugin's configuration fields and read/write; other modules consume through an explicit interface. |
| Game input handling | src/input/input.h/.cpp | Owns event translation/key handling; does not own rendering or INI implementation. |
| Settings UI | src/ui/ | Owns UI and interaction; consumes the configuration interface and adds dependencies per the chosen UI library. |
| Rendering features | src/render/ | Split external entry, hook, shader management, and concrete passes by actual complexity. |
| D3D utilities used in several places | src/render/dx11/ | Only the device/state utilities actually needed; do not copy the whole utility library. |
| One event or engine hook | The matching business module, or src/events / src/hooks when needed | Whether the directory exists in the reference project does not decide whether it is right. |
| Small utilities shared by several modules | Near the consumers; src/base/ only when sharing is real | Do not add hash, timer, or projection code for "maybe later". |

A small feature does not need a facade/director/manager layer each; split when
independent responsibility or state lifecycle appears. Without rendering
needs, do not create render/shaders or an empty draw().

## Modifying an existing project

Read the callers and the build's source-collection method before moving files
or changing interfaces. Rename directories, include paths, namespaces, CMake
inputs, and tests in one pass. Do not refactor unrelated code to make the tree
resemble the reference project. Introduce an original business module only
when the user's request actually touches that business.
