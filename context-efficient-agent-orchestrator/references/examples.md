# Decomposition Examples

## Example 1: Codebase performance investigation

User goal: identify why one stage of a GPU pipeline is slow.

Good decomposition:

- Locator pass: inspect profiler output, call graph, and symbol index.
- Task A: inspect kernel occupancy and memory access for the identified hot kernel.
- Task B: inspect host-device synchronization and stream usage around the stage.
- Task C: inspect allocation lifetime only if profiling indicates allocation overhead.
- Main agent: merge findings against measured timings.

Avoid sending the entire repository to every task. Give each task the profiler fragment, the relevant symbols, and only shared type definitions that it needs.

## Example 2: Large document analysis

User goal: compare obligations, exceptions, and risks across a long agreement.

Good decomposition:

- Build a heading and clause index first.
- Split by obligation family rather than equal page counts.
- Share only defined terms used across multiple sections.
- Require every material claim to cite a clause locator.
- Dispatch an independent reviewer only for clauses that change the risk conclusion.

Avoid using one summary of the entire agreement as evidence for every subagent.

## Example 3: Independent architecture review

User goal: decide whether to transform point clouds before or after merging them.

Good decomposition:

- Task A: analyze computational complexity, memory traffic, and launch structure.
- Task B: analyze data ownership, synchronization, and failure modes.
- Task C: independently review the small set of pipeline definitions and benchmark results that determine the decision.

Mark Task C's duplicated scope as intentional. Do not let the independent-review mode cause unrelated files to be duplicated.

A complete GPU-oriented example is available at `assets/example-plan.json`.

## Example 4: Do not delegate

User goal: explain a 40-line function with no external dependencies.

Keep the task in one agent. Creating multiple task packets, materializing the same short function repeatedly, and merging results would add cost without improving context management.

## Example 5: Dependency-aware dispatch

User goal: diagnose a failure spanning parser, validator, and persistence layers.

Plan:

1. Dispatch parser and persistence tasks concurrently because their sources are independent.
2. Dispatch validator analysis after receiving only the parser's confirmed data-shape facts.
3. Pass the dependency summary, not the parser task's full conversation.
4. Merge by failure hypothesis and evidence.

This preserves concurrency while preventing downstream agents from inheriting irrelevant upstream context.
