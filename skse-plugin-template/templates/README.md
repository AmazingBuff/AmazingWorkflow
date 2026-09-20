# {{PROJECT_NAME}}

{{DESCRIPTION}}

Version {{PROJECT_VERSION}}. Runtime selection: {{RUNTIME_SELECTION}}.
Modules: {{FEATURE_SELECTION}}. Project namespace: {{PROJECT_NAMESPACE}}.

This C++23 SKSE scaffold follows Highlight-Lootable-Corpses: one root CMake
target, cmake/Plugin.h.in, PLUGIN_NAMESPACE macros, manual Load/Query/Version
exports, class-based modules, and REX::W32 rendering interfaces.

## Build

Use Windows x64, VS2022 C++, Windows SDK, CMake 3.22+ and vcpkg.
Set VCPKG_ROOT. Configure/build presets use the reference's Release/Debug names
and shared build folder; select configuration explicitly for Visual Studio.

```powershell
git init
git submodule add -b ng https://github.com/alandtse/CommonLibSSE-NG.git extern/CommonLibSSE
git submodule update --init --recursive
cmake --preset Release
cmake --build --preset Release
cpack -C Release --config build/CPackConfig.cmake
```

For Debug use the Debug presets. Commit the real CommonLib gitlink and
.gitmodules. Instead of a submodule you can set COMMONLIBSSE_SOURCE_DIR to
an existing checkout. Dependency defaults match CommonLib 8.0.1 at
d13d10a0ccb4945870eb841bf1ad8a6cf5ed84dd; compare dependencies when updating ng.
The main ZIP contains SKSE/Plugins/{{PROJECT_NAME}}.dll, README and LICENSE.
The separate symbols ZIP contains its PDB. DLL output is build/Release/.
COPY_OUTPUT defaults OFF; to enable it set COMPILED_PLUGINS_PATH to a mod Data
root (the build appends SKSE/Plugins). Match compiler and vcpkg CRT/toolset.

## Runtime

Install the DLL under Data/SKSE/Plugins along with matching SKSE/Address Library.
Logs use the standard Skyrim documents SKSE directory.
With config selected, the INI is Data/SKSE/Plugins/{{PROJECT_NAME}}.

Hotkey is a Windows virtual-key code like the reference (118 / 0x76 = F7),
converted to a keyboard scan code by InputManager. Zero disables it. Settings
load at plugin Load and save on kSaveGame. Renderer/InputManager install on
NewGame/PostLoadGame; hit/vtable modules install at DataLoaded.
The render callback is a deliberate extension point, with no visible drawing
until project-specific passes are added. D3D11StateCapture/compile_shader are
reused from the reference; capture/restore the states each new pass changes.
No corpse search, QuickLoot, MCP, menu assets or product shaders are generated.

VR is explicit and the flat Present/vtable examples reject VR. Verify ABI,
metadata declarations and game behavior in every runtime before distribution.

## License

Generated project code is GPL-3.0-or-later; see LICENSE. The renderer utility
retains its original AmazingBuff attribution from Highlight-Lootable-Corpses.
New plugin metadata credits {{AUTHOR}}. CommonLib keeps its own GPL and exception
terms; inspect the pinned dependency's COPYING.txt and EXCEPTIONS.md.
