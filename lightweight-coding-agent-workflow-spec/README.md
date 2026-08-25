# Lightweight Coding Agent Workflow v0.5

A two-phase coding workflow with a host-neutral Core and explicit host adapters:

1. The current user-facing task plans and freezes an implementation contract.
2. Exactly one implementation worker writes and verifies through one compatible `VERIFIED` adapter.

The workflow has no service, database, network dependency, package-manager dependency, or executable orchestration runtime. A standard-library-only development validator checks the source package and optional installed copy; it is not part of task execution.

## Architecture

```text
Planner Skill ──loads──> Core Protocol
      │                    │
      ├──classifies──> Documentation Impact
      ├──validates──> Host Adapter Contract
      ├──freezes────> Contract + Git boundary + coding-rule paths
      │                    │
      └──selects exactly one VERIFIED Adapter
                               │
                               └──dispatches one implementation worker
```

Core owns contract, phase, worktree, single-writer, documentation, version-control authority, and result rules. The Adapter Contract defines exactly nine capabilities. A host adapter maps those capabilities without leaking host paths, worker names, model resolution, or lifecycle terminology into Core.

The Planner completes the adapter gate before requesting implementation approval or allowing product-code writes. Missing, ambiguous, incompatible, incomplete, or non-`VERIFIED` adapters produce `CAPABILITY_UNAVAILABLE`; user consent cannot promote an adapter, and the Planner does not implement as a fallback.

## Support matrix

| Host or artifact | State | Protocol / adapter | Surfaces | Product writes |
| --- | --- | --- | --- | --- |
| Codex | `VERIFIED` | `0.5` / `codex` `0.5` | Desktop, CLI, IDE extension | Yes, after approval and revalidation |
| DeepSeek Harness | `EXPERIMENTAL` | `0.5` / `dsh` `0.5` | Web GUI candidate mapping | No |
| Generic adapter template | `AUTHORING_ONLY` | `0.5` / placeholder | Authoring reference | No |
| Claude Code, Cursor, OpenCode, Gemini CLI | `UNSUPPORTED` | none | none | No |
| Any unnamed host | `UNSUPPORTED` | none | none | No |

Only `VERIFIED` is write-eligible. DSH remains a non-dispatchable artifact until its full checklist has retained evidence and a deliberate future release changes its metadata.

## Source package

```text
lightweight-coding-agent-workflow-spec/
├── CHANGELOG.md
├── DESIGN.md
├── README.md
├── agents/
│   └── lightweight_implementer.toml
├── docs/features/
│   ├── README.md
│   └── feature-documentation.md
├── tests/
│   └── test_validate_package.py
├── tools/
│   └── validate_package.py
└── skills/lightweight-coding-workflow/
    ├── SKILL.md
    ├── agents/openai.yaml
    ├── assets/
    │   ├── feature-document.md
    │   ├── implementation-contract.md
    │   └── coding-rules/
    │       ├── manifest.json
    │       ├── README.md
    │       ├── small-project-code-contract/...
    │       ├── small-project-cpp-rules/...
    │       └── small-project-python-rules/...
    └── references/
        ├── protocol.md
        ├── adapter-contract.md
        ├── feature-documentation-convention.md
        ├── git-commit-convention.md
        └── adapters/
            ├── codex.md
            ├── dsh.md
            └── template.md
```

Key references:

- [Design and compatibility](DESIGN.md)
- [Feature-document index](docs/features/README.md)
- [Planner Skill](skills/lightweight-coding-workflow/SKILL.md)
- [Core protocol](skills/lightweight-coding-workflow/references/protocol.md)
- [Host Adapter Contract](skills/lightweight-coding-workflow/references/adapter-contract.md)
- [Feature Documentation Convention](skills/lightweight-coding-workflow/references/feature-documentation-convention.md)
- [Canonical Git commit and Changelog convention](skills/lightweight-coding-workflow/references/git-commit-convention.md)
- [Verified Codex Adapter](skills/lightweight-coding-workflow/references/adapters/codex.md)
- [Experimental DSH Adapter](skills/lightweight-coding-workflow/references/adapters/dsh.md)
- [Authoring-only Adapter Template](skills/lightweight-coding-workflow/references/adapters/template.md)
- [Bundled coding-rule provenance](skills/lightweight-coding-workflow/assets/coding-rules/README.md)
- [Bundled coding-rule integrity manifest](skills/lightweight-coding-workflow/assets/coding-rules/manifest.json)
- [Deterministic validator](tools/validate_package.py)
- [Validator tests](tests/test_validate_package.py)

## Release and compatibility

Protocol `0.5` is the coherent reconciliation release. It retains the two phases, one writer, explicit model choice, bounded Git authority, bundled coding-rule components, and feature-documentation policy while making these rules consistent across Core, adapters, contracts, documentation, and results.

The write gate is stricter than the historical `0.4` package: `EXPERIMENTAL` artifacts can no longer dispatch after user consent. The Codex adapter is released and validated at protocol/adapter `0.5` rather than relying on an older compatibility range. Approved historical contracts are not rewritten; continue them only with matching historical resources, or plan and approve a new `0.5` revision.

The custom Agent TOML and UI metadata remain model-neutral and version-neutral. The Agent omits `model`, `model_reasoning_effort`, and `sandbox_mode`; the Codex adapter validates the task-specific model resolution and preserves the parent task's live permissions.

## Installation and discovery

This package distinguishes the deployment currently used on this machine from portable authoring and discovery locations:

- Current local deployment: copy `skills/lightweight-coding-workflow/` to `%USERPROFILE%\.codex\skills\lightweight-coding-workflow\`, and copy `agents/lightweight_implementer.toml` to `%USERPROFILE%\.codex\agents\lightweight_implementer.toml`.
- Portable Skill authoring/discovery: current [official Codex Skill documentation](https://developers.openai.com/codex/skills) lists repository `.agents/skills` locations from the working directory through the repository root, plus user `$HOME/.agents/skills` and admin `/etc/codex/skills`.
- Custom Agent discovery: current [official Codex subagent documentation](https://developers.openai.com/codex/subagents) lists personal `~/.codex/agents/` and project `.codex/agents/` TOML locations.

These are explicit location choices, not an automatic migration promise. This package does not claim that Codex copies, migrates, or synchronizes a `.codex` Skill deployment with `.agents/skills`; choose one intended Skill location and verify the exact installed copy. Restart Codex if a newly copied Skill or custom Agent does not appear.

From the package root, verify the currently used user-level deployment with:

```powershell
python -B tools/validate_package.py --package . --installed-skill "$env:USERPROFILE\.codex\skills\lightweight-coding-workflow" --installed-agent "$env:USERPROFILE\.codex\agents\lightweight_implementer.toml"
```

The implementation worker validates source only. Installation into a user-level directory is a separate Planner action after source validation and requires the applicable filesystem authority.

## Use

Invoke the Skill explicitly or describe a matching two-phase request:

```text
Use $lightweight-coding-workflow to plan this change with me.
After I approve the plan, use <implementation-model> for implementation.
```

On Codex, the verified Adapter keeps task records under `.codex/task-runs/<task-id>/`. The workflow does not modify `.gitignore` automatically.

Every proposal classifies Documentation Impact as `create`, `update`, or `not-required`. Required feature documentation and its index are part of the same logical boundary as implementation, tests, necessary Changelog, and configuration. Git commit and push authorities remain separate and default to `none`.

Bundled coding-rule components are ordinary package assets listed as absolute paths in an approved contract; they are not separately installed Skills and do not depend on another specification at runtime. Their [manifest](skills/lightweight-coding-workflow/assets/coding-rules/manifest.json) covers every bundled rule file with SHA-256, provenance, and synchronization metadata. Any intentional bundled-file change must update the corresponding manifest entry in the same change.

## Author another adapter

Start from the [authoring template](skills/lightweight-coding-workflow/references/adapters/template.md) and satisfy the [Host Adapter Contract](skills/lightweight-coding-workflow/references/adapter-contract.md). The template remains `AUTHORING_ONLY`, and a candidate remains non-write-capable until all operations have retained evidence and a deliberate versioned release marks it `VERIFIED`.

## Validate

With Python 3.11 or newer (for the standard-library `tomllib` parser), run the test suite and then validate the source package:

```powershell
python -B -m unittest discover -s tests -p "test_*.py"
python -B tools/validate_package.py --package .
```

The validator deterministically checks current-version declarations, package-relative Markdown links and anchors, Skill/adapter front matter, Agent TOML, UI YAML, exact adapter metadata and capability sets, the write gate, operation mappings, unresolved placeholders outside templates, feature-documentation integration, required sections, host-neutral Core language, bundled-rule manifest file sets and hashes, trailing whitespace, and optional source/install parity.

The authoritative behavior and acceptance scenarios are defined in [DESIGN.md](DESIGN.md).
