# Configuration Reference

## Contents

1. Configuration precedence
2. Modes
3. Budget fields
4. Source-selection policy
5. Expansion policy
6. Dispatch and cache policy
7. Merge policy
8. Capability adapters
9. Token and overlap metrics
10. Recommended tuning

## 1. Configuration precedence

Resolve settings in this order:

1. Explicit request or API arguments.
2. Project configuration.
3. Mode profile.
4. `assets/default-config.yaml`.

Keep the resolved values in the plan's `budget` and mode fields so that execution is reproducible.

## 2. Modes

| Mode | Primary goal | Accidental overlap | Deliberate review | Typical use |
|---|---|---:|---:|---|
| `lean` | Lowest context cost | Very low | Rare | Broad repository triage, cheap first pass |
| `balanced` | Cost-quality balance | Low | Targeted | Normal engineering and document analysis |
| `independent-review` | Independent verification | Low outside review scope | Moderate | Architecture decisions, disputed findings |
| `high-assurance` | Maximum evidence quality | Controlled | High | Security, legal, safety, release-critical work |

Mode changes defaults, not hard requirements. Explicit caller settings always win.

## 3. Budget fields

The plan's `budget` object uses these fields:

- `max_subagents`: maximum number of dispatched task packets.
- `max_input_tokens_per_task`: estimated upper bound for one task packet plus materialized sources.
- `max_total_dispatched_tokens`: estimated upper bound across all task invocations.
- `max_accidental_overlap_ratio`: maximum accidental duplicate source tokens divided by total dispatched source tokens.
- `max_shared_source_tokens_per_task`: maximum raw source tokens copied into every task through `shared_context.source_ids`.

Treat budget violations as validation errors. Treat unknown estimates as uncertainty that must be surfaced rather than silently ignored.

## 4. Source-selection policy

Use a stable source ID and an opaque URI. The URI may be a path, object key, document ID, database record, API resource, or connector reference.

Supported selector shapes:

```json
{"type":"lines","start":120,"end":380}
{"type":"pages","start":5,"end":9}
{"type":"symbol","name":"transform_points"}
{"type":"section","heading":"Memory ownership"}
{"type":"object","key":"customer/1234"}
{"type":"query","query":"cuda stream synchronization","top_k":5}
{"type":"whole"}
```

Prefer selectors that remain stable as content changes. Symbol, section, and object selectors are generally more stable than line ranges. Add a `content_hash` or version identifier when stale-source detection matters.

A main agent should read only enough source content to establish routing. A subagent should begin with only its listed source IDs. Narrow follow-up reads are handled through expansion. Shared source IDs are inherited by default; set `inherit_shared_sources: false` on synthesis-only or otherwise exempt tasks so common raw material is not copied unnecessarily.

## 5. Expansion policy

Each task declares:

```json
{
  "mode": "request",
  "max_additional_tokens": 4000
}
```

- `deny`: no additional reads.
- `request`: subagent returns requests; scheduler decides.
- `bounded`: subagent may expand directly within the token limit.

Use `request` as the default when the scheduler can perform an approval round. Use `bounded` when latency matters and the file tool can enforce accounting. Use `deny` only for strict evaluation or fully self-contained packets.

Every expansion must be appended to the result packet with the actual or estimated token cost.

## 6. Dispatch and cache policy

Use this prompt layout:

1. Stable role and response contract.
2. Stable project definitions that every task needs.
3. Compact shared facts and constraints.
4. Task objective, questions, stop conditions, and dependency summaries.
5. Materialized source fragments.

Do not reorder or wrap stable prefixes unnecessarily when the host supports prefix caching. Do not add unrelated sources to chase a cache hit. Cached tokens can still consume context capacity and distract the model.

Set `pass_parent_transcript: false`. Transform parent state into explicit facts and source references instead.

## 7. Merge policy

Recommended defaults:

- `strategy`: `evidence-weighted`
- `conflict_policy`: `independent-review-on-material-conflict`
- `deduplicate_by`: normalized claim plus source locator
- `require_source_version_match`: true for mutable repositories or documents

A material conflict is one that changes a decision, severity, recommendation, numerical result, or user-facing conclusion. Do not trigger a reviewer for stylistic differences.

## 8. Capability adapters

A host scheduler only needs five operations:

```text
inventory(scope) -> source summaries
materialize(source descriptor) -> source content
invoke(agent profile, task packet, materialized content) -> result packet
approve(expansion request) -> approved source descriptors
gather(result packets) -> merge input
```

Optional operations:

```text
estimate_tokens(content or source descriptor)
hash(source)
persist(fact or index)
load_persisted(key)
```

Keep source materialization outside the planner. This prevents the planner from accidentally embedding complete files into every packet.

## 9. Token and overlap metrics

Let `R(t)` be the set of source IDs materialized for task `t`, including shared source IDs. Let `size(s)` be the estimated token count for source `s`.

Estimated source tokens for a task:

```text
source_tokens(t) = sum(size(s) for s in R(t))
```

Estimated total task input:

```text
task_input(t) = source_tokens(t) + estimated_packet_tokens(t)
```

Estimated total dispatched input:

```text
total_input = sum(task_input(t) for all tasks t)
```

Raw duplicate source tokens:

```text
raw_duplicate = sum(size(s) * max(0, readers(s) - 1) for all sources s)
```

Raw overlap ratio:

```text
raw_overlap_ratio = raw_duplicate / total_dispatched_source_tokens
```

Accidental duplicate tokens exclude occurrences marked `intentional_overlap` and exclude sources explicitly placed in shared context. The validator applies `max_accidental_overlap_ratio` to this metric.

When no tokenizer is available, the bundled validator estimates prompt tokens from text length using a conservative character-based approximation. Treat it as planning guidance, not billing truth.

## 10. Recommended tuning

### Small repository or document set

- `max_subagents`: 2 to 3
- Use `balanced`.
- Permit small whole files.
- Keep shared raw sources below 1,500 tokens per task.

### Large monorepo or corpus

- `max_subagents`: 4 to 8, constrained by real parallel capacity.
- Require symbol, section, query, or line selectors.
- Persist source maps and hashes.
- Use a low accidental-overlap limit.

### High-assurance review

- Use `high-assurance`.
- Mark the exact duplicated review scope as intentional.
- Keep all unrelated modules non-overlapping.
- Require direct evidence and a final conflict reviewer only when findings disagree materially.

### Latency-sensitive CLI agent

- Use `balanced` with `bounded` expansion.
- Generate packets before spawning tasks.
- Dispatch dependency-free tasks concurrently.
- Pass compact dependency summaries to downstream tasks.
- Record measured token usage to improve future estimates.
