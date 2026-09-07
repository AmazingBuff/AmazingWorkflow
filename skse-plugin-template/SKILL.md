---
name: skse-plugin-template
description: Use only when the active host Skill catalog reports lightweight-coding-workflow enabled and discoverable; requires its canonical rules to scaffold or maintain a C++23 Skyrim SKSE plugin for SE, AE, or VR.
---

# SKSE Plugin Template

This Skill generates one CommonLibSSE-NG plugin project. It is not
standalone: it requires the `lightweight-coding-workflow` skill's coding-rule
authority.

**Presence gate**: before doing anything else, ask the active host Skill
catalog whether `lightweight-coding-workflow` is enabled and discoverable. If
catalog metadata is unavailable, inspect loaded Skill metadata, then host-native
roots including `$CODEX_HOME/skills/`, `~/.codex/skills/`, `~/.zcode/skills/`,
`~/.agents/skills/`, `<project>/.zcode/skills/`, and
`<project>/.agents/skills/`. Filesystem presence alone is insufficient: require
both enabled and discoverable status. If that status is unavailable, stop and
report that the required coding-rule authority is missing; do not scaffold with
a local rule copy, fallback, or synthesized rules.

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

## PLAN external-research binding

The generic conditional `External Research Gate` belongs to
`lightweight-coding-workflow`; this section binds Skyrim-specific triggers to
that gate and does not create a second research policy. Mark research
`required` before approving plugin architecture that depends on CommonLib or
SKSE APIs, ABI or layout-sensitive code, relocation or vtable hooks, rendering
or `Present`, event/input/serialization/Papyrus integration, SE/AE/VR runtime
differences, new dependencies, or copied third-party design. These triggers
apply even when a local prototype exists if mature upstream or GitHub prior
art is likely.

The proposal and its Evidence Packet record the target runtime(s), CommonLib
branch/version, upstream and implementation maintenance status, license and
reuse status, and the relevant implementation differences. For low-level or
non-trivial architecture, require authoritative CommonLib/SKSE evidence plus a
maintained implementation matching the target runtime, or document why only
one source exists. Check Address Library/relocation identifiers, vtable or
layout assumptions, renderer lifecycle, and runtime-specific branches rather
than treating a copied snippet as authority. If required evidence is
unavailable or insufficient, return to PLAN before approving or changing the
architecture; never invent a Skyrim-compatible design. Trivial mechanical
metadata or changes fully determined by local code/tests/canonical project
documentation may be marked not-required with an explicit reason.

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
