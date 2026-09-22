# CMake: keep the organization, configure contents by feature

## Root file order

Follow the root CMake organization of Highlight-Lootable-Corpses:

1. project with version, namespace, author, and runtime options.
2. CMake module path; generated material and source file sets as needed.
3. configure_file to generate build/src/plugin.h and the version resource.
4. add_library(SHARED) with C++23, compile/link options, and include directories.
5. Actual dependencies, find_package, target_link_libraries, PCH.

Keep the root-file pattern that manages the target centrally by default; a
src/CMakeLists.txt is not needed. main.cpp already defines the Load/Query/
Version exports, so a helper that would generate the same exports must not be
used alongside it.

The template keeps the reference project's Release configure preset and the
build/ directory:

```powershell
cmake --preset Release
cmake --build build --config Release
```

Without buildPresets you cannot use `--build --preset Release`. Visual Studio
is a multi-config generator; the actual build configuration is selected by
`--config`. The original reference environment used MSVC 14.44.35207 and
x64-windows-static-md; the template keeps that environment as an example. When
porting to another machine, adjust the toolset selection in presets and the
target together to match the dependencies' CRT/STL, and do not treat the exact
patch version as a universal requirement for all SKSE projects.

## Dependency layering

By default the target directly depends only on CommonLib, fmt, and spdlog.
DirectXMath, DirectXTK, and rapidcsv in vcpkg serve the current CommonLib
build; do not remove them merely because first-party code does not call them.
Conversely, the reference project's SimpleIni, SKSE-MCP, and the like must not
all be added without a feature need.

Every time a feature is added, check together: whether the root manifest needs
a new port, whether CMake needs find_package or add_subdirectory, which target
should link it, and whether any runtime plugin still needs to be installed by
the user.

| Feature | Necessary delta example |
| --- | --- |
| INI | With SimpleIni: add simpleini to the manifest; find_package(simpleini CONFIG REQUIRED); link SimpleIni::SimpleIni. |
| MCP menu | Only when this UI approach is selected: add the extern/SKSE-MCP submodule, add_subdirectory, and link SKSE-MCP::SKSE-MCP. |
| Custom D3D rendering | Add d3d11/dxgi according to the actual API; d3dcompiler is only needed to compile HLSL at runtime. |
| Pure game events | CommonLib is usually enough; no UI or rendering dependency required. |

Never merely link a library in CMake while omitting the vcpkg/submodule entry,
and never copy a manifest entry without an actual consumer. Validate new
dependency versions against the target runtime and the selected
CommonLib/toolchain branch, checking their maintenance status, license, and
implementation differences; the baseline is a project decision, not a business
property that must be copied.

## Source files and shaders

The template keeps the reference's GLOB_RECURSE; re-run configure after adding
source files. If the target project should notice new files automatically, you
may deliberately adopt CONFIGURE_DEPENDS or an explicit list, state its
behavior, and keep one clear strategy.

Only bring in the reference's cmake/embed_shaders.cmake when custom shaders
are actually needed. Put the HLSL that is really used in src/render/shaders,
list "file:symbol-name" explicitly, and output to
build/src/render/shader_sources.h; the custom command's DEPENDS should include
both the HLSL files and the generating script, and the generated header joins
the plugin target. Check the consumer's includes and build dependencies so
that shader edits actually trigger regeneration and recompilation. Without
shaders, do not keep empty mappings, generation commands, or a ShaderManager.

## Release and verification

packaging.cmake is only the reference's CPack organization example; the
current minimal template has no plugin install rules. Define the install
layout for DLL, configuration, assets, and symbols when the user asks for a
release package, then inspect the ZIP; do not claim an empty configuration
already produces an installable mod package. COPY_OUTPUT, deployment scripts,
and machine-local paths are added only when needed.

Verification scope follows the change: the default minimal plugin should
configure, compile, link, and have its exports and generated metadata checked;
new configuration checks defaults/invalid values/read-write; new input or a
hook requires real in-game verification; new shaders check dependency
rebuilding and the compile entry point. When reusing a local dependency
cache, record it explicitly; it is not equivalent to a fresh dependency
installation succeeding.

## Build wiring when using features

`--features` wires the deltas above into the root CMake through each package's
feature.json instead of duplicating a full root configuration. When no feature
is selected, the conditional placeholder blocks are removed and the base
template gains neither the sources nor the dependencies. shaders declares the
generated header with include(cmake/shaders.cmake) and that header joins the
root target; menu separately adds SKSE-MCP; config separately adds SimpleIni.
Dependent features expand in order and are deduplicated. Never hand-copy only
a feature's sources while skipping these build steps.
