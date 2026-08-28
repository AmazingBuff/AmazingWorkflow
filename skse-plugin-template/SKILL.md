---
name: skse-plugin-template
description: Scaffold or maintain a canonical-rule-compliant C++23 Skyrim SKSE plugin for SE, AE, and VR with alandtse/CommonLibSSE-NG branch ng, project namespaces, CMake 3.25 Debug/Release presets, optional config/hotkey/Present/vtable/event modules, GPL-3.0-or-later output, and direct use of the sibling lightweight-coding-workflow skill's coding-rule authority. Use only when the lightweight-coding-workflow skill is installed and discoverable; when it is absent, this skill does not apply - report that the required rule authority is missing instead of proceeding without it.
---

# SKSE Plugin Template

This Skill generates one CommonLibSSE-NG plugin project. It is not
standalone: it requires the `lightweight-coding-workflow` skill's coding-rule
authority.

**Presence gate**: before doing anything else, locate the
`lightweight-coding-workflow` skill through the host's skill-discovery
mechanism (loaded skill metadata, the skill catalog, or an installed skills
directory such as `<project>/.zcode/skills/`, `<project>/.agents/skills/`,
`~/.zcode/skills/`, or `~/.agents/skills/`). Do not assume a relative
sibling path and do not proceed by guessing. If the skill is not installed
and discoverable, stop and report that the required coding-rule authority is
missing; do not scaffold with a local rule copy, fallback, or synthesized
rules.

Once located, use the canonical rule documents **within that skill's
directory**:

- `[lightweight-coding-workflow root]/assets/coding-rules/small-project-cpp-rules/SKILL.md` (C++ rule index)
- `[lightweight-coding-workflow root]/assets/coding-rules/small-project-code-contract/SKILL.md` (shared code contract)
- `[lightweight-coding-workflow root]/assets/coding-rules/manifest.json` (hash inventory)

A local rule copy, fallback, symlink, or second hash inventory is forbidden;
the discovered skill's rule paths are part of the required execution context.

## When to use

- Create a new Skyrim SE/AE/VR SKSE DLL project.
- Add or maintain INI configuration, Present-frame hotkeys, a safe D3D11
  Present overlay, a vtable hook, or a hit-event sink.
- Verify that an existing generated project still follows this package's
  runtime, build, dependency, Git, and license invariants.

## Scaffold

Run from this Skill directory:

```powershell
python scripts/scaffold.py --name My_Plugin --author "Your Name" --dir C:/work/My_Plugin
python scripts/scaffold.py --help
```

The generator validates every input before reporting success. `--name` must be
a CMake/C++ identifier and is normalized to a lowercase hyphenated vcpkg name
plus a lowercase snake-case C++ root namespace. Camel-case boundaries become
underscores, repeated underscores collapse, and C++ keywords receive a
`_plugin` suffix; the reserved standard namespace name `std` is handled the
same way.
`--baseline` is exactly 40 hexadecimal characters. Author values reject unsafe
CMake/C++ delimiters; descriptions support quotes through context-specific
escaping but reject multiline/control/template-delimiter input.

Supported runtime values are `all`, `se`, `ae`, `vr`, `se-ae`, `se-vr`,
and `ae-vr`. Supported features are `config`, `present_hook`, `hotkey`,
`vtable_hook`, and `event_sink`. `hotkey` requires both `config` and
`present_hook` because the Present callback invokes the generated
`<project>::input::poll()`.

Only `alandtse/CommonLibSSE-NG` branch `ng` is supported. `--git-init` is
local-only. `--add-commonlib-submodule` is separately named and
network-capable; it runs:

```powershell
git init
git submodule add -b ng https://github.com/alandtse/CommonLibSSE-NG.git ext/CommonLibSSE
```

Default generation runs neither command and creates no `.gitmodules`. After a
real submodule add, commit both `.gitmodules` and the
`ext/CommonLibSSE` gitlink.

## Execution rules

1. Read [multi-runtime.md](references/multi-runtime.md) before changing runtime
   options, address resolution, or plugin metadata.
2. Read [build-and-verify.md](references/build-and-verify.md) before changing
   presets, CommonLib/vcpkg acquisition, dependencies, or build boundaries.
3. Pass the presence gate above before any scaffold or maintenance work.
   Before C++ or CMake work, read every applicable document from the
   discovered `lightweight-coding-workflow` skill's
   `assets/coding-rules/small-project-cpp-rules/SKILL.md` C++ rule index and
   its `assets/coding-rules/small-project-code-contract/SKILL.md` shared
   code contract.
4. Keep the generator, every template, generated README/license/resource
   metadata, and the two focused references consistent.

## Generated project contract

The generated root `CMakeLists.txt` owns project metadata, `COPY_OUTPUT`,
runtime options, and CommonLib source discovery. CommonLib is loaded from
`ext/CommonLibSSE` or `COMMONLIBSSE_SOURCE_DIR`; the source target uses
`add_commonlibsse_plugin(...)` with explicit first-party sources. CommonLib
generates plugin Query/version metadata and VERSIONINFO resources. Do not add
hand-written Query/version exports, a fixed runtime list, global warning flags,
or an exact MSVC patch pin.

Every first-party declaration is under the normalized lowercase snake-case
project namespace and lowercase module namespaces, except required external
ABI/framework names such as `SKSEPlugin_Load` and `ProcessEvent`. Keep
first-party `.h.in` templates lowercase while retaining conventional CMake and
generated-project documentation filenames.

Feature ownership is fixed:

| Feature | Generated responsibility |
| --- | --- |
| `config` | `config::load()` owns persisted state; the mutex protects copies and atomics carry render-thread values. |
| `present_hook` | `esp_renderer::install()` runs after data loaded and records D3D11 work on a deferred context. |
| `hotkey` | Requires `config` and `present_hook`; `input::poll()` reads atomic configuration at the start of Present. |
| `vtable_hook` | `hooks::install()` resolves the Character vtable through `RE::VTABLE_Character` and `REL::Relocation`. |
| `event_sink` | `hit_events::install()` registers a process-lifetime static sink. |

`main.cpp` initializes logging, calls `SKSE::Init`, registers one message
listener, and dispatches selected Load/Data-loaded glue. Present code keeps only
device-bound helpers across frames, resets them on device change, uses local
per-frame COM references, executes the deferred command list with state
restoration, and never retains a swap-chain back buffer or render-target view.
The SKSE Load/message boundaries and the Present callback catch failures before
crossing their external ABI boundaries and always preserve the original Present
call. Input, allocation, locking, and file I/O are not marked `noexcept` unless
their implementation has a real no-throw guarantee.

## Build and external boundaries

Generated projects expose Debug and Release configure/build presets inherited
from a hidden Visual Studio 2022 x64 `msvc` base:

```powershell
cmake --preset "msvc debug"
cmake --build --preset "msvc debug"
cmake --preset "msvc release"
cmake --build --preset "msvc release"
```

Default scaffolding is local and does not initialize Git or fetch CommonLib.
`--git-init` is local-only; `--add-commonlib-submodule` is the explicitly named
network-capable option and creates the `ext/CommonLibSSE` submodule. Generated
output defaults to GPL-3.0-or-later; CommonLibSSE-NG's upstream Modding and
Linking Exceptions remain unchanged.
