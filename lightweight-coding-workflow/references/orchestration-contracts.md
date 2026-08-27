# Orchestration Contracts (Scout Edition)

Contract version: `0.6` (part of the Core protocol at the same version).

Field contracts for the Phase 1 scout orchestration defined in the [Context Routing reference](context-routing.md). These are the shapes `scripts/validate_plan.py` checks and `scripts/build_task_packets.py` generates; the machine-readable source of truth for plan validation is `assets/context-routing/orchestration-plan.schema.json`. This is a self-contained coding-scoped copy of the general orchestration contracts, trimmed to what scout routing uses.

## 1. Source descriptor

```json
{
  "id": "src-payment-controller",
  "uri": "src/api/payment_controller.py",
  "selector": {
    "type": "symbol",
    "name": "PaymentController.submit"
  },
  "estimated_tokens": 1400,
  "purpose": "Payment submission endpoint, timeout configuration, retry behavior",
  "summary": "Optional routing summary; not a substitute for evidence",
  "content_hash": "optional-version-or-hash"
}
```

Rules:

- `id` must be unique within a plan.
- `uri` is a repository-relative path or host-resolvable reference.
- `selector` must identify the smallest useful source unit.
- `estimated_tokens` covers materialized source content, not prompt instructions.
- `summary` may support routing but must not be cited as primary evidence when the original source is available.

Supported selector shapes:

```json
{"type":"lines","start":120,"end":380}
{"type":"pages","start":5,"end":9}
{"type":"symbol","name":"transform_points"}
{"type":"section","heading":"Memory ownership"}
{"type":"object","key":"customer/1234"}
{"type":"query","query":"timeout propagation","top_k":5}
{"type":"whole"}
```

Prefer selectors that remain stable as content changes: symbol, section, and object selectors are generally more stable than line ranges. Add `content_hash` or a version identifier when stale-source detection matters.

## 2. Shared fact

```json
{
  "id": "fact-timeout-window",
  "statement": "Timeouts occur between 5 and 8 seconds after payment submission.",
  "provenance": [],
  "confidence": "confirmed",
  "always_share": true
}
```

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
  "plan_id": "payment-timeout-investigation",
  "goal": "Locate the cause of intermittent payment timeouts and gather evidence for an implementation contract.",
  "mode": "balanced",
  "assumptions": [],
  "budget": {
    "max_subagents": 3,
    "max_input_tokens_per_task": 12000,
    "max_total_dispatched_tokens": 26000,
    "max_accidental_overlap_ratio": 0.1,
    "max_shared_source_tokens_per_task": 1200
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

`budget.max_input_tokens_per_task` constrains the initial dispatch estimate only; expansion allowances are excluded and the validator warns when the worst case (initial plus expansion) exceeds the cap. `max_total_dispatched_tokens` likewise excludes expansion allowances.

A complete plan has at least one task and one source unless every task operates only on dependency results.

## 4. Scout task definition and generated task packet

A scout task definition in the plan:

```json
{
  "id": "task-db-scout",
  "agent_role": "db-scout",
  "objective": "Determine whether connection-pool lease behavior explains intermittent timeouts.",
  "dependencies": [],
  "source_ids": ["src-db-pool"],
  "questions": [
    "Can pool exhaustion delay connection acquisition past the client timeout?",
    "Are leases released on all failure paths?"
  ],
  "deliverable": "Findings on pool behavior under load with exact locators.",
  "evidence_required": true,
  "intentional_overlap": false,
  "capabilities": ["materialize", "code-analysis"],
  "allowed_expansion": {
    "mode": "request",
    "max_additional_tokens": 2000
  },
  "stop_conditions": [
    "All lease acquisition and release paths in scope are accounted for."
  ]
}
```

Scout tasks use `deny` or `request` expansion only; `bounded` self-expansion is forbidden by the Context Routing reference.

`build_task_packets.py` converts this into a standalone packet containing:

- Parent goal and plan mode.
- Applicable shared facts, assumptions, and constraints.
- Assigned source descriptors, not source bytes. A task may set `inherit_shared_sources` to `false` when it operates only on dependency results or does not need the shared raw sources.
- Dependencies and a placeholder for compact dependency summaries.
- Execution rules and the evidence-packet contract.
- Estimated input metrics.

The Planner materializes source bytes after packet generation. It must not attach the complete parent transcript.

## 5. Expansion request

```json
{
  "request_id": "expand-task-db-scout-1",
  "task_id": "task-db-scout",
  "missing_information": "The pool configuration is read from a module not in the assigned scope.",
  "requested_source": {
    "uri": "src/db/config.py",
    "selector": {
      "type": "symbol",
      "name": "POOL_SETTINGS"
    }
  },
  "reason": "Needed to determine whether the configured lease time can exceed the client timeout.",
  "estimated_tokens": 250
}
```

The Planner should approve, narrow, replace, or deny the request. Approved sources must be recorded in the evidence packet.

## 6. Evidence packet (scout result)

```json
{
  "schema_version": "1.0",
  "packet_type": "subagent-result",
  "plan_id": "payment-timeout-investigation",
  "task_id": "task-db-scout",
  "status": "complete",
  "summary": "Pool exhaustion is plausible: the 30-second lease is not released on the early-return path.",
  "findings": [
    {
      "id": "finding-lease-leak",
      "claim": "The lease is not released when validation fails before the query executes.",
      "severity": "high",
      "confidence": "high",
      "evidence": [
        {
          "source_id": "src-db-pool",
          "locator": "src/db/connection_pool.py:112-128",
          "note": "Early return path skips the release call present on the success path."
        }
      ],
      "recommendation": "Release the lease on all exit paths; prefer a context manager."
    }
  ],
  "facts_for_parent": [
    {
      "statement": "The connection pool caps at 20 connections with a 30-second lease.",
      "provenance": ["src-db-pool"],
      "confidence": "confirmed"
    }
  ],
  "assumptions": [],
  "unknowns": [],
  "expansion_requests": [],
  "expansions_used": []
}
```

Valid status values are `complete`, `partial`, and `blocked`. A `partial` or `blocked` result must explain what is missing. `metrics` (measured token usage) is optional; a scout that cannot measure usage reports the field as absent rather than inventing numbers.

An evidence packet must not contain private chain-of-thought. Findings, evidence, concise rationale, and uncertainty are sufficient.

## 7. Merge into planning

Scouts do not produce a separate merge report. The Planner merges evidence packets by claim and locator, deduplicates facts, prefers direct evidence over summaries and confirmed facts over inference, and records remaining uncertainty in the proposal. Surviving locators flow into the contract's Discovery section and are referenced by requirements and acceptance criteria.

## 8. Compatibility rules

- Additive fields are allowed; consumers must ignore unknown fields.
- Increment `schema_version` for breaking field or semantic changes.
- Preserve source IDs and task IDs across retries when the logical unit is unchanged.
- Keep source content out of the plan and packet by default. Source bytes belong to the materialization step.
