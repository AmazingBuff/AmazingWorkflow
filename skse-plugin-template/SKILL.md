---
name: skse-plugin-template
description: Create or maintain C++23 SKSE plugins following the Highlight-Lootable-Corpses project pattern, including root CMake, Plugin.h metadata macros, class-based modules, INI settings, input events and REX D3D11 hooks.
---

# SKSE Plugin Template

This template is rebuilt from the structure of Highlight-Lootable-Corpses.
Use that project's architectural pattern, rather than introducing a separate
generic CommonLib helper-based scaffold. Read
[reference-project.md](references/reference-project.md) for the source mapping.

## Project pattern

The template tree mirrors a project directly:

```text
templates/
  CMakeLists.txt
  CMakePresets.json
  vcpkg.json
  LICENSE
  README.md
  .gitignore
  cmake/
    Plugin.h.in
    version.rc.in
    packaging.cmake
  src/
    main.cpp
    pch.h
    config/config.{h,cpp}
    input/input.{h,cpp}
    render/renderer.{h,cpp}
    render/present_hook.{h,cpp}
    render/dx11/d3d11_util.{h,cpp}
    events/hit_events.{h,cpp}
    hooks/hooks.{h,cpp}
```

- One root CMakeLists creates the SHARED target, gathers src sources, configures
  Plugin.h and the RC resource, adds extern/CommonLibSSE and links dependencies.
- Plugin.h provides PLUGIN_NAMESPACE/BEGIN/END and Plugin::Plugin_Name,
  Plugin_Version and Plugin_Author. Keep the reference's logger alias and
  class/module conventions; substitute the new project namespace and author.
- main.cpp defines SKSEPlugin_Load, SKSEPlugin_Query and SKSEPlugin_Version
  explicitly, like the reference. Do not add add_commonlibsse_plugin or a second
  generated metadata translation unit.
- Setting owns Config and INI I/O; InputManager owns event registration;
  Renderer delegates to an internal OverlayDirector; PresentHook::instance()
  owns its original callback, installation and state. Use REX::W32 interfaces.
- Render utilities retain the reference's immediate-context state-capture and
  shader-compilation pattern. Do not replace them with the former DirectXTK
  BasicEffect/deferred esp_renderer design.

The template intentionally omits corpse scanning, loot filters, QuickLoot,
SKSE-MCP UI, mask/icon passes and their shaders. Add those only for a requested
feature. A generic render callback remains an explicit extension point with
no visible drawing, rather than copying game-specific product behavior.

## Generate

From this skill directory (or use an absolute path to the script):

```powershell
python scripts/scaffold.py --name MyPlugin --author "Your Name" --dir C:/work/MyPlugin
python scripts/scaffold.py --name BarePlugin --features none --dir C:/work/BarePlugin
python scripts/scaffold.py --help
```

Defaults: SE/AE, config + hotkey + present_hook. Other supported optional
modules are event_sink and vtable_hook. The generator reads templates/src
directly and selects module files; there is no templates/features directory.
hotkey requires config only. VR must be explicit, with a compatible selection
such as --runtimes vr --features config,hotkey,event_sink. The flat Present and
Character-vtable examples reject VR until a verified adaptation is supplied.

Output must be absent or empty. Generation is offline by default; --git-init
initializes a repository and --add-commonlib-submodule also fetches the ng
CommonLib submodule. Commit the real gitlink and .gitmodules. Source generation
does not implicitly deploy into Skyrim.

Names, author, description, version and baseline are validated before writing.
Names derive a snake-case namespace and hyphenated package name. Version limits
are major/minor <=255 and patch <=4095, matching SKSE's packed representation.
The same inputs produce the same files.

## Runtime lifecycle

| Phase | Default action |
| --- | --- |
| Load | Module-reset workaround, logging, SKSE::Init, Setting::load, checked message listener. |
| DataLoaded | Optional HitEvents and Hooks installation. |
| NewGame / PostLoadGame | Renderer and InputManager installation. |
| SaveGame | Setting::save. |
| Keyboard event | Convert configured virtual-key code to scan code, toggle on IsDown. |
| Present | Serialized render callback, followed by saved original Present. |

Hotkey config retains the reference's **Windows virtual-key codes**, e.g. F7 =
118 / 0x76; zero disables it. Do not silently migrate it to scan-code storage.
Successful registration and hook installation must be idempotent. Keep null
checks and exception containment at external callbacks, and avoid noexcept on
methods doing allocation, locking or file I/O without containment.

## Build and maintenance

Read [build-and-verify.md](references/build-and-verify.md) for presets, dependencies,
package layout and validation. Read [multi-runtime.md](references/multi-runtime.md)
before changing engine ABI, metadata, hooks or renderer state management.

Inspect project instructions and existing conventions first. If the host exposes
lightweight-coding-workflow, use its canonical C++ and shared coding-rule
references when applicable; do not duplicate their files here. The explicit
reference-project architecture in this skill takes precedence over older
template preferences. Do not require unavailable discovery APIs or invent gates.

Keep scripts, templates and documentation synchronized. For existing projects,
inspect before migration; the generator does not overwrite them. Verify against
the actual CommonLib revision rather than assuming a current ng branch matches
the recorded snapshot. Keep source, compile/link, and live-game evidence distinct.
