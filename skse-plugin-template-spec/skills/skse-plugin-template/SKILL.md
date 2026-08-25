---
name: skse-plugin-template
description: Scaffold or maintain a C++23 Skyrim SKSE plugin for SE, AE, and VR with alandtse/CommonLibSSE-NG branch ng, validated metadata, official plugin declarations, reproducible CMake presets, optional config/hotkey/Present/vtable/event modules, GPL-3.0-or-later output, and offline package tests.
---

# SKSE Plugin Template

This Skill generates one CommonLibSSE-NG plugin project without requiring
another workflow package. Its bundled coding rules are self-contained under
`assets/coding-rules/` and integrity-checked by
`assets/coding-rules/manifest.json`.

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
a CMake/C++ identifier and is normalized to a lowercase hyphenated vcpkg name.
`--baseline` is exactly 40 hexadecimal characters. Author values reject unsafe
CMake/C++ delimiters; descriptions support quotes through context-specific
escaping but reject multiline/control/template-delimiter input.

Supported runtime values are `all`, `se`, `ae`, `vr`, `se-ae`, `se-vr`,
and `ae-vr`. Supported features are `config`, `present_hook`, `hotkey`,
`vtable_hook`, and `event_sink`. `hotkey` requires both `config` and
`present_hook` because the Present callback invokes `Input::poll()`.

Only `alandtse/CommonLibSSE-NG` branch `ng` is supported. `--git-init` is
local-only. `--add-commonlib-submodule` is separately named and
network-capable; it runs:

```powershell
git init
git submodule add -b ng https://github.com/alandtse/CommonLibSSE-NG.git extern/CommonLibSSE
```

Default generation runs neither command and creates no `.gitmodules`. After a
real submodule add, commit both `.gitmodules` and the
`extern/CommonLibSSE` gitlink.

## Execution rules

1. Read [structure.md](references/structure.md) before changing generated file
   ownership or lifecycle glue.
2. Read [multi-runtime.md](references/multi-runtime.md) before changing runtime
   options, address resolution, or plugin metadata.
3. Read [patterns.md](references/patterns.md) before changing C++ features,
   hooks, event sinks, or Present rendering.
4. Read [build-and-verify.md](references/build-and-verify.md) before changing
   presets, CommonLib/vcpkg acquisition, dependencies, or verification.
5. For C++ and CMake changes, follow the bundled
   [C++ rule index](assets/coding-rules/small-project-cpp-rules/SKILL.md) and
   [shared code contract](assets/coding-rules/small-project-code-contract/SKILL.md).
6. Keep `README.md`, this index, generated README/license/resource metadata,
   all references, tests, integrity manifest, and Changelog synchronized.

Do not replace `add_commonlibsse_plugin(...)` with hand-written Query/version
exports. Do not pin an exact MSVC patch toolset or set global warning flags.
Do not retain swap-chain back buffers or render-target views between Present
calls, and do not draw on the immediate context without complete state
isolation.

## Build and verify

Generated projects expose matching configure and build presets named
`msvc release`:

```powershell
cmake --preset "msvc release"
cmake --build --preset "msvc release"
```

Validate this source package offline from its root:

```powershell
python -B -m unittest discover -s tests -v
python -B tools/validate_package.py .
```

These checks do not download CommonLib/vcpkg packages or claim a Skyrim DLL
build passed. `-B` prevents bytecode artifacts, and validation rejects any
present `__pycache__` directory or `.pyc` file. Generated output defaults to
GPL-3.0-or-later. CommonLibSSE-NG's
own Modding and Linking Exceptions remain upstream terms and are not altered by
this template.
