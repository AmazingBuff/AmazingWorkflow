# Reference-to-template mapping

Source: Highlight-Lootable-Corpses, project HEAD
01e317ceb1e4c96bb6433b767e4baac2e524b1bf, inspected 2026-09-20.
CommonLib source: d13d10a0ccb4945870eb841bf1ad8a6cf5ed84dd, version 8.0.1.
These identify the local evidence, not a claim about the latest upstream release.

The templates directory was rebuilt from empty, not incrementally converted
from its previous features/src-CMake/esp_renderer architecture.

| Source | New template |
| --- | --- |
| Root CMakeLists.txt | Root-only SHARED target, recursive src collection, configured Plugin.h/RC, CommonLib source dependency, scoped compiler/link settings. |
| CMakePresets.json | cmake-dev/vcpkg/windows inheritance, shared build folder, VS2022 x64, Release and Debug configure/build presets. |
| cmake/Plugin.h.in | Same namespace macros and Plugin metadata names, parameterized project and author. |
| src/main.cpp | Explicit Load/Query/Version exports, logger setup and lifecycle dispatch. |
| src/pch.h | RE/REL/SKSE/REX includes, standard literals, logger alias, DLLEXPORT and Plugin.h. |
| src/config/config.* | Config + Setting singleton, get_config/load/save, generic Enabled and VK Hotkey fields. |
| src/input/input.* | InputManager with process-lifetime InputHandler event sink, VK-to-scan conversion. |
| src/render/renderer.* | Renderer facade + private OverlayDirector singleton using REX device/context. |
| src/render/present_hook.* | PresentHook singleton, callback/original members, real swap-chain vtable slot 8. |
| src/render/dx11/d3d11_util.* | Reused compile_shader and D3D11StateCapture with original attribution. |
| cmake/packaging.cmake, LICENSE, .gitignore | Reference packaging pattern, full GPL text and ignore conventions. |

Only scaffolding-specific adjustments are made: validated inputs, project
placeholders, optional modules, configuration defaults, checked registration,
idempotent hooks, NewGame coverage, safe INI access, DLL resource type, working
install rules and portable compiler selection. The exact 14.44.35207 compiler
patch remains a local toolchain choice; dependency compatibility still matters.

Setting::get_config returns a locked copy rather than a shared mutable reference,
with toggle() for input updates. Hotkey values remain VK codes like the source.
Renderer intentionally performs no draw until a product pass is added. The
reference's fixed corpse count, search/filter/UI, QuickLoot, SKSE-MCP, geometry,
icon/mask shaders and cached back-buffer implementation are not generic features.
Optional HitEvents/Hooks follow the class style but are extension examples, not
claims that the reference project contained those exact modules.

The new default does not contain templates/features, src/CMakeLists.txt,
plugin_version.h.in, esp_renderer, add_commonlibsse_plugin, DirectXTK BasicEffect
or a generated discovery metadata source file. Do not reintroduce that old
architecture when maintaining this skill.

Preserve original attribution in the reused D3D utility and the full GPL text.
Plugin author metadata is a generator parameter. Inspect the pinned CommonLib
COPYING.txt/EXCEPTIONS.md when distributing a linked DLL.

## Rebuild verification

On 2026-09-20, seven generator regression groups passed, including all 224 raw
feature/runtime combinations and a check that every file in the new templates
tree is consumed. Skill validation and Release/Debug preset listing passed.
An all-feature SE/AE scaffold configured against the real CommonLib source and
all its new plugin sources compiled/linked in Release with MSVC 19.44.35228 and
Windows SDK 10.0.26100.0. This run reused the matching CommonLib static library
compiled from that same source/runtime/toolset in the earlier verification and
the installed vcpkg cache; it did not rebuild or freshly acquire dependencies.

The rebuilt DLL has exactly Load, Query and Version SKSE exports and a 1.0.0.0
version resource. Main/symbols ZIP contents were inspected. MSVC reports the
reference's benign /Ob2-to-/Ob3 option override. Debug/VR compilation and live
Skyrim behavior remain unverified; do not infer them from this Release result.
