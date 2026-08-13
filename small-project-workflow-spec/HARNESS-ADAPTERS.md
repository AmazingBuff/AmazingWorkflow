# Harness adapters

The canonical workflow remains `SPEC.md` plus the 14 directories in `skills/`.
OpenCode and Pi bundles are generated projections; never edit a generated
bundle as a second workflow source.

## Build OpenCode

First verify the exact model IDs and variants with the target OpenCode runtime.
Then run:

```text
python scripts/build_harness.py --harness opencode --output <project-bundle> --strong-model <provider/model> --execution-model <provider/model> --strong-variant <variant> --execution-variant <variant>
python scripts/validate_bundle.py <project-bundle>
```

Copy the generated `.opencode` directory into the target project's root. Start
or continue the workflow with `/small-project <request>`. The bundle uses one
primary orchestrator and six direct subagents; no nested subagent depth is
required.

## Build Pi

First verify the exact Pi `provider/model` selectors and supported thinking
levels. Pi accepts levels through `max`; Codex-only `ultra` therefore maps to
the verified Pi maximum rather than being copied literally.

```text
python scripts/build_harness.py --harness pi --output <project-bundle> --strong-model <provider/model> --execution-model <provider/model> --strong-thinking max --execution-thinking max
python scripts/validate_bundle.py <project-bundle>
```

Copy the generated `.pi` directory into the target project's root, inspect the
project-controlled agent definitions and extension, then explicitly trust the
project in Pi. Start with `/small-project <request>`. Pi has no built-in
subagent feature; the generated extension launches one isolated, no-session Pi
process for each approved role packet.

## Guarantees and limits

- Every bundle contains exactly 14 skills and an embedded byte-identical copy
  of `SPEC.md` under `small-project-workflow/references/`.
- OpenCode and Pi bundles omit Codex-only `agents/openai.yaml` files.
- Pi hides every phase/language skill from implicit invocation and leaves only
  the workflow orchestrator discoverable by intent.
- The manifest records all file hashes, the resolved model map, and required
  isolation capabilities.
- Builders accept model values only from the caller. Runtime model availability
  and authentication must be verified in the target Harness; they are never
  silently inferred.
- Generated bundle validation is not a live Harness smoke test. OpenCode is
  installed locally but its provider configuration is unavailable here; Pi is
  not installed here. Their manifests therefore keep live discovery marked
  false until tested in the destination project.
