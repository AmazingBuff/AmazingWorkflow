# Orchestration Contracts (Scout Edition)

Contract version: `0.6` (part of the Core protocol at the same version).

Field contracts for the Phase 1 scout orchestration defined in the [Context Routing reference](context-routing.md). These are the shapes `scripts/validate_plan.py` checks and `scripts/build_task_packets.py` generates; the JSON Schemas under `assets/context-routing/` are checked mirrors, not an independent unverified authority. This is a self-contained coding-scoped copy of the general orchestration contracts, trimmed to what scout routing uses.

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

Prefer selectors that remain stable as content changes: symbol, section, and object selectors are generally more stable than line ranges. Add `content_hash` or a source revision/digest when stale-source detection matters; use line ranges only when no stable selector exists.

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
  "schema_version": "1.1",
  "plan_id": "payment-timeout-investigation",
  "goal": "Locate the cause of intermittent payment timeouts and gather evidence for an implementation contract.",
  "mode": "balanced",
  "configuration": {
    "id": "context-routing-defaults",
    "source": "assets/context-routing/default-config.yaml",
    "revision": 1,
    "digest": "sha256:<64-hex-digits>"
  },
  "routing": {
    "decision": "orchestrated",
    "estimated_files": 6,
    "estimated_tokens": 9000,
    "multiple_information_boundaries": true,
    "basis": "The goal crosses multiple information boundaries."
  },
  "discovery_authorization": {
    "authorized": true,
    "scout_model": "user-approved-scout-model",
    "packet_count": 1,
    "token_ceiling": 30000
  },
  "assumptions": [],
  "budget": {
    "max_subagents": 3,
    "max_input_tokens_per_task": 12000,
    "max_total_dispatched_tokens": 30000,
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

`budget.max_input_tokens_per_task` constrains the initial dispatch estimate; the validator reports any task whose initial estimate plus requested allowance exceeds that per-task cap. Mode-profile budget values are maximum limits, so a plan may select lower values. `max_total_dispatched_tokens` is the selected maximum for the whole dispatch, including all declared expansion allowances. The actual approved `discovery_authorization.token_ceiling` must satisfy `worst_case_total_input_tokens <= token_ceiling <= max_total_dispatched_tokens`.

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

Scout tasks use `deny` or `request` expansion only. `request` requires explicit Planner approval before a new source is read.

`build_task_packets.py` converts this into a standalone packet containing:

- Parent goal and plan mode.
- Applicable shared facts, assumptions, and constraints.
- Assigned source descriptors, not source bytes. A task may set `inherit_shared_sources` to `false` when it operates only on dependency results or does not need the shared raw sources.
- Dependencies and a placeholder for compact dependency summaries.
- The explicit discovery authorization and execution rules.
- The exact Evidence Packet schema reference and validation-authority name.
- Estimated input metrics.
- A manifest with the stable generator marker, plan id, exact packet paths, and packet SHA-256 digests.

The Planner materializes source bytes after packet generation. It must not attach the complete parent transcript.

`--overwrite` is accepted only when an existing manifest has that generator marker, matches the new plan id and exact packet paths, and authenticates every packet digest. Unrelated or same-named unauthenticated JSON causes a failure before any deletion.

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
  "schema_version": "1.1",
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
      "id": "fact-db-pool-size",
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

`assets/context-routing/evidence-packet.schema.json` and `scripts/validate_evidence_packet.py` are the checked schema and validation authority for this envelope. Required fields are exactly the fields shown above. Finding severity is `low`, `medium`, `high`, or `critical`; finding confidence is `low`, `medium`, or `high`. Valid status values are `complete`, `partial`, and `blocked`; a `partial` or `blocked` result must list missing information in `unknowns`. `metrics` is optional; a scout that cannot measure usage reports the field as absent rather than inventing numbers.

Expansion requests are proposals only. Every entry in `expansions_used` must reference a request, identify a source locator and token cost, and set `planner_approved` to `true`. A task with `deny` expansion cannot return requests or used expansions. No result may use another expansion mode.

An evidence packet must not contain private chain-of-thought. Findings, evidence, concise rationale, and uncertainty are sufficient.

## 7. Merge into planning

Scouts do not produce a separate merge report. The Planner merges evidence packets by claim and locator, deduplicates facts, prefers direct evidence over summaries and confirmed facts over inference, and records remaining uncertainty in the proposal. Surviving locators flow into the contract's Discovery section and are referenced by requirements and acceptance criteria.

## 8. Compatibility rules

- Additive fields are allowed; consumers must ignore unknown fields.
- Increment `schema_version` for breaking field or semantic changes and update both schemas, validators, and packet envelopes in one logical change.
- Preserve source IDs and task IDs across retries when the logical unit is unchanged.
- Keep source content out of the plan and packet by default. Source bytes belong to the materialization step.
