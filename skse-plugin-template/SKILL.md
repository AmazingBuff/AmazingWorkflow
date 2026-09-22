---
name: skse-plugin-template
description: Plan file layout, configure CMake and adapt selected reusable code for a C++23 SKSE plugin, using Highlight-Lootable-Corpses as an organizational reference. Generate a minimal plugin by default; select reusable modules from templates/features only when needed.
---

# SKSE Plugin Structure and Reuse

This skill mainly guides three things: **how to lay out files, how to
configure CMake, and how to adapt reusable code on demand**.
Highlight-Lootable-Corpses provides the organizational pattern and concrete
implementation reference; it is not a mandatory module checklist. Start from
the plugin's actual features, then choose the directories, dependencies, and
implementations you need.

## Working order

1. Read the existing project and the user request; determine which runtime
   capabilities this change needs. When maintaining an existing project,
   keep its working structure.
2. Present this change's file layout and responsibilities, CMake deltas, and
   the source and trimming scope of any reused code; a brief statement is
   enough for small tasks.
3. For a new project, generate the minimal loadable plugin first, then add
   files for the actual features. Do not pre-build empty modules, and do not
   add a module just because the reference project has one.
4. When selecting a reference implementation, check its dependencies, object
   ownership, calling thread, lifecycle, and runtime fit; strip the original
   business coupling before wiring it in.
5. Verify only what this change actually generates or modifies. Report
   compilation, unit tests, and in-game verification separately.

When used together with lightweight-coding-workflow, lightweight takes
precedence: its Planner manages scope, authorization, implementation
contracts, and verification, and the same implementation worker performs the
generation or modification; this skill only supplements SKSE file
organization, CMake, and code-reuse rules. Existing user authorization
remains valid; do not create a second planning/approval flow or an extra
writer, and do not bypass lightweight's responsibility boundaries.

When this skill is used alone, complete the explicitly requested work
directly once the user has asked for implementation; do not require extra
tasks or repeated authorization for this process.

## PLAN external-research binding

The generic conditional `External Research Gate` belongs to
`lightweight-coding-workflow`; this section binds Skyrim-specific triggers to
that gate and does not create a second research policy. Mark research
`required` before approving plugin architecture that depends on CommonLib or
SKSE APIs, ABI or layout-sensitive code, relocation or vtable hooks, rendering
or `Present`, event/input/serialization/Papyrus integration, differences
between SE, AE, or VR runtimes, new dependencies, or copied third-party
design. These triggers apply even when a local prototype exists if mature
upstream or GitHub prior art is likely.

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

## Default template boundary

```text
CMakeLists.txt          Root file defining the plugin target, dependencies, and compile settings
CMakePresets.json       Toolchain, architecture, vcpkg, and build directories
vcpkg.json             Current dependency manifest
.gitmodules            CommonLib source configuration; does not mean the submodule has been fetched
cmake/
  plugin.h.in          CMake-configured project metadata and namespace
  version.rc.in        Windows DLL version resource
  packaging.cmake      Kept as a build-organization example; define actual install contents separately when releasing
src/
  main.cpp             Logging, SKSE initialization, and exports
  pch.h                Core headers and project-wide aliases
```

A default generated project **does not include** config, input, ui, render,
base utilities, event/vtable hooks, ShaderManager, SKSE-MCP, shaders, or any
game business code, and it registers no message/event handler without a
purpose. The CommonLib transitive dependency in the template does not mean the
plugin already implements those features.

```powershell
python scripts/scaffold.py --name MyPlugin --namespace MyTeam --author "Your Name" --dir C:/work/MyPlugin
```

The output directory must be empty; by default the generator only writes
files. `--git-init` only initializes local Git; `--add-submodules` fetches the
CommonLib and selected-feature submodules. `--display-name` only sets the
README title and does not automatically bring in a menu.

## On-demand features

Optional modules live in `templates/features/<name>/`. Without `--features`
the minimal template above is still generated.

```powershell
python scripts/scaffold.py --name MyPlugin --features input --dir C:/work/MyPlugin
python scripts/scaffold.py --name MyPlugin --features config,input,menu --dir C:/work/MyPlugin
python scripts/scaffold.py --name MyPlugin --features render,shaders --dir C:/work/MyPlugin
```

Dependencies are completed and deduplicated automatically; for example
`input` automatically includes `config`; menu or render are not selected
automatically. `--features none` explicitly selects the minimal template;
`all` suits validating the full set and is not the default recommendation.
Each feature contains a feature.json plus the src/cmake subtree to copy into
the project root. The generator wires up files, CMake, vcpkg, submodules,
includes, and the corresponding lifecycle entries. The output directory must
still be empty; for an existing project migrate item by item against the
manifest instead of overwriting existing code. See
[features.md](references/features.md) for details.

## Three kinds of reference

- [file-layout.md](references/file-layout.md): add files by responsibility;
  keep entry-file and shared-header boundaries.
- [build-and-verify.md](references/build-and-verify.md): root CMake
  organization, on-demand dependency/asset wiring, and verification.
- [reuse-guide.md](references/reuse-guide.md): select reference code, strip
  business coupling, and keep interfaces and call chains consistent.
- [reference-project.md](references/reference-project.md): reading entry into
  the reference project and the patterns worth learning.
- [multi-runtime.md](references/multi-runtime.md): read when the work involves
  engine events, hooks, rendering, or cross-runtime concerns.

"Staying consistent" means adopting clear responsibility boundaries, build
organization, and traceable adaptation. It does not require matching the
reference project's file count, module set, dependency list, business
behavior, or code hashes. Do not require modifying the reference project
before fixing the target project, and do not use file-by-file equality checks
to block necessary trimming.

## Validating the skill

```powershell
python scripts/test_scaffold.py
python -X utf8 <skill-creator-root>/scripts/quick_validate.py <skill-directory>
```

By default run two representative cases: the minimal plugin boundary, and
the config + shaders dependency and generation wiring. To verify a single
affected behavior, pass the specific unittest test name; run
`python scripts/test_scaffold.py --full` explicitly only when maintaining
the generator's dependency resolution or when a full regression is genuinely
needed before a release — do not make the full matrix the daily default.

Ordinary plugin tasks select only the 1–2 cases actually affected this time;
using the template does not justify running the generator's full test suite.
When combined with lightweight-coding-workflow, follow the Verification and
Codex test budgets of the implementation contract. Report compilation,
in-game verification, and unverified parts separately.
