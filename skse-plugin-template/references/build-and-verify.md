# Build and verification

## Build contract

Use Windows x64, Visual Studio 2022/v143, Windows SDK, CMake 3.22+, C++23 and
vcpkg. The root CMake owns the single plugin target. src has no CMakeLists.
Sources use GLOB_RECURSE CONFIGURE_DEPENDS to follow the reference's source-tree
pattern while noticing added modules. Generated Plugin.h is in build/src and
version.rc is in build; the resource type is DLL.

Use add_library(SHARED), not add_commonlibsse_plugin. main.cpp already owns all
three SKSE exports; introducing the helper duplicates discovery exports.
Metadata stays sourced from project version/name/author through Plugin.h.

```powershell
git init
git submodule add -b ng https://github.com/alandtse/CommonLibSSE-NG.git extern/CommonLibSSE
git submodule update --init --recursive
cmake --preset Release
cmake --build --preset Release
cmake --preset Debug
cmake --build --preset Debug
cpack -C Release --config build/CPackConfig.cmake
```

Set VCPKG_ROOT first. The presets inherit cmake-dev, vcpkg and windows, matching
the reference. Both configurations share build/, with explicit configuration
in build presets (CMAKE_BUILD_TYPE does not select a VS configuration).
The DLL is build/Release/<name>.dll. CPack creates a main ZIP with
SKSE/Plugins/<name>.dll, README and LICENSE, and a separate PDB ZIP.

The root prefers extern/CommonLibSSE, with COMMONLIBSSE_SOURCE_DIR as an optional
local source override. Default generation is offline and doesn't initialize Git.
--git-init is local-only; --add-commonlib-submodule performs the acquisition
above except the recursive update. Commit .gitmodules and the actual gitlink.
If acquisition fails after files are generated, inspect them rather than
rerunning into the now nonempty directory.

## Dependencies and compiler

Default manifest constraints match the inspected CommonLib 8.0.1 manifest at
d13d10a0ccb4945870eb841bf1ad8a6cf5ed84dd, baseline
ee12231b20c95013c6638d845d04c91559a1d1ff. Root vcpkg installs dependencies;
the embedded subdirectory manifest is not recursively installed. The reference
plugin's older reduced manifest is insufficient as the library's dependency
authority. Compare manifests when acquiring a newer ng revision.

Match x64-windows-static-md with /MD Release or /MDd Debug. Match MSVC toolsets
of plugin and cached libraries. The source project's exact compiler patch
pin is a local workaround, not a mandatory installed version for all users.
Set a local user preset toolset if needed and rebuild mismatched dependencies.
Never hide an unresolved __std_* symbol mismatch by changing warnings.

CommonLib may fetch patch-safety sources or prebuilt dependencies while
configuring. An offline generator does not guarantee an offline build. Use
cached ports and explicit FetchContent source overrides for offline checks.
Only directly link feature libraries as needed (SimpleIni, user32,
d3d11/dxgi/d3dcompiler). CommonLib may independently require DirectXTK.

COPY_OUTPUT defaults OFF. Explicitly enabling it requires
COMPILED_PLUGINS_PATH to a mod Data root; SKSE/Plugins is appended. Build-only
work does not request overwriting a live game installation.

## Verify

```powershell
python scripts/test_scaffold.py
python <skill-creator-root>/scripts/quick_validate.py <skill-directory>
```

Generate a minimal (--features none), default, and all-feature project. Check
the template/source tree, selected module dependencies and valid JSON. List
configure/build presets. Configure against real CommonLib, build Release and
Debug where available, inspect one copy of each SKSE export and the RC version,
and inspect ZIP entries. State whether libraries were reused from a matching
cache or freshly built; neither proves a fresh vcpkg install succeeded.

For runtime claims verify Load, DataLoaded, NewGame, repeated save loads,
SaveGame INI persistence, keyboard repeats/menus and rendering in each claimed
executable. Compilation is not live-game evidence.

## Migrate from the previous skill output

This is a replacement architecture, not a source-compatible template update.
Move target construction to root; remove src/CMakeLists and helper-generated
metadata; replace plugin_version.h.in with Plugin.h.in and update callers.
Replace namespace free functions with Setting/InputManager/Renderer/PresentHook
module APIs. Use Release/Debug presets and the root build output location.
Previous revision scan-code INIs require explicit migration back to VK values
(F7 65 becomes 118); already-reference-compatible VK files need no migration.
Do not apply both changes to the same file. Preserve existing user projects
until their callers and build integration have been reviewed.
