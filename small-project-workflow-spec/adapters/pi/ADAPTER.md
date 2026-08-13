# Pi adapter source

This directory is source material for rendering the small-project workflow for
[Pi](https://github.com/earendil-works/pi). It deliberately supplies no model
defaults. Use the suite-level `scripts/build_harness.py` builder; do not copy
unrendered templates.

The builder renders every `agents/*.md.tmpl` file with the required values in
[`harness.json`](harness.json), places the resulting Markdown files in
`.pi/agents/`, installs `prompts/small-project.md` in `.pi/prompts/`, and copies
the complete `extensions/small-project-subagents/` directory to
`.pi/extensions/small-project-subagents/`. Install the byte-identical source
`SPEC.md` at `.pi/skills/small-project-workflow/references/SPEC.md` and install
the whole `skills/` package together under `.pi/` so the workflow can retain
its authoritative specification.

`/small-project` is the main-session orchestrator entry point. The extension
adds only `small_project_subagent`, which accepts one of the six fixed roles:
`decision`, `implementer`, `reviewer`, `test-planner`, `test-runner`, or
`reporter`. It discovers only the nearest project `.pi/agents` directory; it
does not read user-level agents and it does not execute the unrendered
`adapters/pi/agents` source files. This is why the builder must install the
rendered agents into `.pi/agents`.

Security matters here. Pi extensions execute with full permissions, and this
extension starts a separate Pi process with `--approve`. The extension first
requires Pi project trust and then loads the repository-controlled agent prompt
from `.pi/agents`; do not trust a project before reviewing those files. The
implementer and test runner intentionally expose Pi's `bash` tool. Their
delegated work therefore requires a usable Bash/shell tool in the Pi runtime;
the other role templates omit it. Review the rendered tool lists, model
selectors, and thinking values before enabling the extension.

The extension validates each rendered `provider/model-id` selector against
Pi's available model registry. A missing, unauthenticated, malformed, or
unrendered model is returned as `CAPABILITY_UNSATISFIED`; there is no silent
model or thinking downgrade.

Pi is not installed in the current development environment, so the source and
generated bundle can be statically validated here but live extension discovery
must be verified in an installed, trusted Pi project before claiming runtime
completion.
