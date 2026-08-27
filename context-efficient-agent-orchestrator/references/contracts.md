# Orchestration Contracts

## Contents

1. Source descriptor
2. Shared fact
3. Orchestration plan
4. Task packet
5. Expansion request
6. Result packet
7. Merge report
8. Compatibility rules

The machine-readable source of truth for plan validation is `assets/orchestration-plan.schema.json`.

## 1. Source descriptor

```json
{
  "id": "src-transform-kernel",
  "uri": "src/transform.cu",
  "selector": {
    "type": "lines",
    "start": 120,
    "end": 380
  },
  "estimated_tokens": 2800,
  "purpose": "CUDA point transformation kernel and launch code",
  "summary": "Optional routing summary; not a substitute for evidence",
  "content_hash": "optional-version-or-hash"
}
```

Rules:

- `id` must be unique within a plan.
- `uri` is opaque to the skill and interpreted by the host adapter.
- `selector` must identify the smallest useful source unit.
- `estimated_tokens` covers materialized source content, not prompt instructions.
- `summary` may support routing but must not be cited as primary evidence when the original source is available.

## 2. Shared fact

```json
{
  "id": "fact-point-layout",
  "statement": "Each input point is represented as float4.",
  "provenance": ["src-point-api"],
  "confidence": "confirmed",
  "always_share": false
}
```

`always_share` is optional and defaults to `false`. Set it to `true` only when every task genuinely needs the fact regardless of which sources it reads.

Valid confidence values are `confirmed`, `inferred`, and `unverified`. An inferred fact must remain labeled as inference through downstream packets and final synthesis.

Fact routing rule: a shared fact is delivered only to tasks whose assigned sources intersect the fact's `provenance` (including inherited shared sources). Two exceptions bypass this filter:

- A fact with empty `provenance` is delivered to every task.
- A fact with `always_share: true` is delivered to every task regardless of provenance.

If a synthesis-only task with `inherit_shared_sources: false` needs a provenanced fact, mark that fact `always_share: true`; otherwise the routing rule will silently drop it from the task's packet.

## 3. Orchestration plan

Minimal shape:

```json
{
  "schema_version": "1.0",
  "plan_id": "plan-example",
  "goal": "Evaluate a multi-module implementation and produce evidence-backed fixes.",
  "mode": "balanced",
  "assumptions": [],
  "budget": {
    "max_subagents": 4,
    "max_input_tokens_per_task": 16000,
    "max_total_dispatched_tokens": 52000,
    "max_accidental_overlap_ratio": 0.15,
    "max_shared_source_tokens_per_task": 1500
  },
  "shared_context": {
    "facts": [],
    "constraints": [],
    "source_ids": []
  },
  "sources": [],
  "tasks": [],
  "merge": {
    "strategy": "evidence-weighted",
    "conflict_policy": "independent-review-on-material-conflict",
    "final_checks": []
  }
}
```

The complete plan includes at least one task and one source unless every task operates only on dependency results.

## 4. Task definition and generated task packet

A task definition in the plan:

```json
{
  "id": "task-kernel",
  "agent_role": "cuda-reviewer",
  "objective": "Determine whether the point-transform launch and indexing are correct.",
  "dependencies": [],
  "source_ids": ["src-transform-kernel", "src-point-api"],
  "questions": [
    "Can any thread access a point outside the valid range?",
    "Is the matrix layout used consistently?"
  ],
  "deliverable": "Prioritized findings with exact source locators and concrete fixes.",
  "evidence_required": true,
  "intentional_overlap": false,
  "inherit_shared_sources": true,
  "capabilities": ["materialize", "code-analysis"],
  "allowed_expansion": {
    "mode": "request",
    "max_additional_tokens": 4000
  },
  "stop_conditions": [
    "All listed questions are answered or explicitly blocked."
  ]
}
```

`build_task_packets.py` converts this into a standalone packet containing:

- Parent goal and plan mode.
- Applicable shared facts, assumptions, and constraints.
- Assigned source descriptors, not source bytes. A task may set `inherit_shared_sources` to `false` when it operates only on dependency results or does not need the shared raw sources.
- Dependencies and a placeholder for compact dependency summaries.
- Execution rules and the result contract.
- Estimated input metrics.

The scheduler must materialize source bytes after packet generation. It must not attach the complete parent transcript.

## 5. Expansion request

```json
{
  "request_id": "expand-task-kernel-1",
  "task_id": "task-kernel",
  "missing_information": "The kernel uses a macro whose definition is not in the assigned scope.",
  "requested_source": {
    "uri": "include/cuda_macros.hpp",
    "selector": {
      "type": "symbol",
      "name": "CUDA_CHECK"
    }
  },
  "reason": "Needed to determine whether launch errors are synchronized and surfaced.",
  "estimated_tokens": 250
}
```

The scheduler should approve, narrow, replace, or deny the request. Approved sources must be recorded in the result packet. `metrics` in the result packet is optional; a subagent that cannot measure token usage reports the field as absent rather than inventing numbers.

## 6. Result packet

```json
{
  "schema_version": "1.0",
  "packet_type": "subagent-result",
  "plan_id": "plan-example",
  "task_id": "task-kernel",
  "status": "complete",
  "summary": "The launch bounds are safe, but matrix indexing is inconsistent with the declared layout.",
  "findings": [
    {
      "id": "finding-matrix-layout",
      "claim": "The kernel reads the matrix as column-major while the host fills it as row-major.",
      "severity": "high",
      "confidence": "high",
      "evidence": [
        {
          "source_id": "src-transform-kernel",
          "locator": "lines 184-201",
          "note": "Indexing pattern uses column-major offsets."
        },
        {
          "source_id": "src-point-api",
          "locator": "lines 61-72",
          "note": "Host API documents row-major input."
        }
      ],
      "recommendation": "Normalize the host and kernel to one documented layout."
    }
  ],
  "facts_for_parent": [
    {
      "statement": "The launch includes an index guard before point access.",
      "provenance": ["src-transform-kernel"],
      "confidence": "confirmed"
    }
  ],
  "assumptions": [],
  "unknowns": [],
  "expansion_requests": [],
  "expansions_used": [],
  "metrics": {
    "measured_input_tokens": 4200,
    "measured_output_tokens": 900
  }
}
```

Valid status values are `complete`, `partial`, and `blocked`. A `partial` or `blocked` result must explain what is missing.

A result packet must not contain private chain-of-thought. Findings, evidence, concise rationale, and uncertainty are sufficient.

## 7. Merge report

Recommended shape:

```json
{
  "plan_id": "plan-example",
  "status": "complete",
  "synthesis": "Concise final answer or decision.",
  "accepted_findings": ["finding-matrix-layout"],
  "rejected_findings": [],
  "conflicts": [],
  "remaining_unknowns": [],
  "budget": {
    "estimated_total_input_tokens": 12000,
    "measured_total_input_tokens": 11820,
    "accidental_overlap_ratio": 0.0
  }
}
```

For every rejected material finding, retain a short evidence-based rejection reason. For unresolved conflicts, state the decision impact.

## 8. Compatibility rules

- Additive fields are allowed.
- Consumers must ignore unknown fields unless strict mode is explicitly enabled.
- Increment `schema_version` for breaking field or semantic changes.
- Preserve source IDs and task IDs across retries when the logical unit is unchanged.
- Add attempt IDs separately; do not mutate the task identity.
- Keep source content out of the plan and packet by default. Source bytes belong to the materialization layer.
