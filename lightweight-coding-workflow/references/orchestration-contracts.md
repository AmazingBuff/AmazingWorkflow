# PLAN Task Contracts

Contract version: `0.7` (part of the Core protocol at the same version).

These field contracts define the direct routing record, minimal micro-task
envelope, batch PLAN plan, generated task packet, and Evidence Packet. The
semantic authorities are `scripts/validate_plan.py`,
`scripts/build_task_packets.py`, and `scripts/validate_evidence_packet.py`;
the JSON schemas under `assets/context-routing/` are checked mirrors.

## 1. Task capability

Supported PLAN task kinds are exactly:

```text
requirement-research | repository-read | dependency-check | evidence-analysis
```

`implementation` is a WORK-only capability. The stable host Agent id
`lightweight_scout` may implement all four PLAN kinds, but each invocation is
task-scoped and read-only. It never authors a plan or implementation contract.

## 1a. External Research Gate

Every non-trivial coding proposal includes an `external_research` object in
PLAN. Its decision is `required`, `recommended`, or `not-required`; its reason
and status are explicit. The object also records mode, decision-critical and
architecture-relevant flags, evidence bar, source ids, citations, limitations,
uncertainty, risk, stop conditions, conflicts, conflict resolution, fallback,
and a host capability check.

Required triggers are external APIs/ABIs/frameworks, runtime or version
compatibility, low-level hooks or integration patterns, new dependencies,
license-sensitive reuse, and locally unsupported designs with likely mature
prior art. Trivial/mechanical work and changes fully determined by local code,
tests, and canonical documentation may be not-required. Required
decision-critical research cannot be approved while unavailable or
insufficient; recommended research can continue only with explicit uncertainty
and risk.

External source records use stable ids and direct URLs and include source kind,
repository/project, revision, retrieval date, license/reuse status,
target-version/runtime applicability, relevant locator, confidence, and
conflicts. The normal architecture bar is one authoritative upstream source
plus one maintained matching implementation, or a documented single-source
reason. Cached/indexed search is the default; live search is used when
freshness, release/branch, issue state, or compatibility may change. Stop when
the evidence bar is met, contradictions are resolved/disclosed, marginal value
falls below cost, or the budget is exhausted.

Only `requirement-research` and `dependency-check` tasks may request
`managed-web-research`. The capability is read-only, has no shell-network or
external-mutation authority, and is not promoted from documentation alone.
Unavailable capability records a direct-Planner, uncertain, or blocked
fallback. WORK returns to PLAN if missing external evidence would alter the
contract.

The gate may be `pending` while an eligible task is dispatched with an
available, verified, read-only request using the gate's mode. The dispatch is
evidence gathering, not approval evidence. Research tasks may begin with an
exact query and budget and return newly discovered external source records;
the source id, URL, revision, date, license/reuse status, applicability,
locator, confidence, and conflicts travel with the Evidence Packet. A local
task in a mixed batch returns `external_sources: []` and
`research_result.status: "not-required"` with mode `"none"`.
For a web request, only the authorized query/questions, mode, budget, and stop
conditions are in scope. URLs discovered by that query need no per-result
expansion approval; an additional query, domain, or scope requires an
expansion request, and discovery grants no download, reuse, write, or mutation
authority.

## 2. Context-economics record

Every delegated routing record contains:

```json
{
  "planner_context_savings": 900,
  "delegated_input_tokens": 500,
  "estimated_result_tokens": 120,
  "coordination_overhead_tokens": 200,
  "weighted_cost_savings": 50,
  "weighted_cost_rationale": "The bounded read removes a larger Planner context slice; total tokens may increase.",
  "independently_describable": true,
  "evidence_already_present": false,
  "continuous_planner_judgment": false,
  "total_token_savings_claimed": false
}
```

The decision is beneficial when Planner-context savings exceed coordination
overhead or weighted-cost savings are positive, provided the task is
independently describable and its evidence is not already present. These are
estimates for context and weighted cost, not a claim of fewer total tokens.

## 3. Direct routing record

Direct handling is represented without task or source packet data:

```json
{
  "schema_version": "2.1",
  "envelope_type": "routing-decision",
  "plan_id": "payment-timeout-plan",
  "goal": "Decide whether repository reading is needed.",
  "routing": {
    "decision": "direct",
    "estimated_files": 1,
    "estimated_tokens": 200,
    "multiple_information_boundaries": false,
    "basis": "The answer is already present in the Planner context.",
    "economics": {
      "planner_context_savings": 0,
      "delegated_input_tokens": 0,
      "estimated_result_tokens": 0,
      "coordination_overhead_tokens": 200,
      "weighted_cost_savings": 0,
      "weighted_cost_rationale": "Direct handling avoids unnecessary coordination.",
      "independently_describable": false,
      "evidence_already_present": true,
      "continuous_planner_judgment": false
    }
  },
  "external_research": {
    "decision": "not-required",
    "reason": "The answer is already in Planner context and no external design evidence is needed.",
    "status": "not-required",
    "mode": "none",
    "decision_critical": false,
    "architecture_relevant": false,
    "evidence_bar": "not-applicable",
    "target_applicability": {
      "target_versions": ["not-applicable"],
      "target_runtimes": ["not-applicable"],
      "notes": "No external target applies."
    },
    "source_ids": [],
    "sources": [],
    "evidence": [],
    "limitations": [],
    "uncertainty": "No external research was needed.",
    "risk": "A later architecture decision must reevaluate the gate.",
    "stop_conditions": ["The Planner context is sufficient."],
    "conflicts": [],
    "conflict_resolution": "No material conflict identified.",
    "fallback": "not-applicable",
    "host_capability": {
      "capability": "managed-web-research",
      "status": "not-checked",
      "mode": "none",
      "read_only": true,
      "shell_network": false,
      "external_mutations": false,
      "verified": false,
      "verification_method": "not-applicable",
      "verification": "No managed web search was requested."
    }
  }
}
```

## 4. Minimal micro-task envelope

A micro task is one independently describable PLAN evidence request. It does
not require a full orchestration plan or batch merge:

```json
{
  "schema_version": "2.1",
  "envelope_type": "micro-task",
  "plan_id": "payment-timeout-plan",
  "task_id": "read-timeout-setting",
  "task_kind": "repository-read",
  "agent_id": "lightweight_scout",
  "goal": "Locate the payment timeout setting.",
  "objective": "Read the endpoint definition and identify its timeout value.",
  "query": "Which timeout does PaymentController.submit configure?",
  "sources": [
    {
      "id": "src-controller",
      "uri": "src/api/payment_controller.py",
      "selector": {"type": "symbol", "name": "PaymentController.submit"},
      "estimated_tokens": 300,
      "purpose": "Endpoint timeout configuration",
      "source_kind": "local-code"
    }
  ],
  "deliverable": "One fact with a precise source locator.",
  "stop_conditions": ["The timeout value and its locator are identified."],
  "evidence_required": true,
  "allowed_expansion": {"mode": "deny", "max_additional_tokens": 0},
  "budget": {
    "estimated_input_tokens": 500,
    "max_input_tokens": 1000,
    "max_result_tokens": 300
  },
  "economics": {
    "planner_context_savings": 900,
    "delegated_input_tokens": 500,
    "estimated_result_tokens": 120,
    "coordination_overhead_tokens": 200,
    "weighted_cost_savings": 50,
    "weighted_cost_rationale": "The bounded read removes a larger Planner context slice; total tokens may increase.",
    "independently_describable": true,
    "evidence_already_present": false,
    "continuous_planner_judgment": false
  },
  "plan_task_policy": {
    "model": "gpt-5.6-luna",
    "reasoning_effort": "max",
    "max_concurrent_tasks": 2,
    "max_estimated_input_tokens_per_round": 12000,
    "pass_parent_transcript": false,
    "sandbox_mode": "read-only",
    "allow_writes": false,
    "allow_external_mutations": false,
    "user_visible_dispatch_notice": true,
    "per_task_approval_required": false,
    "over_policy": "user-approval-or-direct-fallback",
    "managed_web_research": {
      "capability": "managed-web-research",
      "allowed_task_kinds": ["dependency-check", "requirement-research"],
      "allowed_modes": ["cached-indexed", "live"],
      "read_only": true,
      "shell_network": false,
      "external_mutations": false,
      "unavailable_fallback": "direct-planner-or-blocked"
    }
  },
  "plan_task_authorization": {
    "authorized": true,
    "model": "gpt-5.6-luna",
    "reasoning_effort": "max",
    "task_count": 1,
    "token_ceiling": 1000
  },
  "model_override": {
    "model": "gpt-5.6-luna",
    "reasoning_effort": "max",
    "explicit": true
  },
  "external_research": {
    "decision": "not-required",
    "reason": "The local source determines this bounded lookup.",
    "status": "not-required",
    "mode": "none",
    "decision_critical": false,
    "architecture_relevant": false,
    "evidence_bar": "not-applicable",
    "target_applicability": {
      "target_versions": ["not-applicable"],
      "target_runtimes": ["not-applicable"],
      "notes": "No external target applies to this local lookup."
    },
    "source_ids": [],
    "sources": [],
    "evidence": [],
    "limitations": [],
    "uncertainty": "No external research was needed.",
    "risk": "A later architecture choice must reevaluate the gate.",
    "stop_conditions": ["The local fact is located."],
    "conflicts": [],
    "conflict_resolution": "No material conflict identified.",
    "fallback": "not-applicable",
    "host_capability": {
      "capability": "managed-web-research",
      "status": "not-checked",
      "mode": "none",
      "read_only": true,
      "shell_network": false,
      "external_mutations": false,
      "verified": false,
      "verification_method": "not-applicable",
      "verification": "No managed web search was requested."
    }
  },
  "response_contract": {
    "schema_version": "2.1",
    "packet_type": "subagent-result",
    "schema_ref": "assets/context-routing/evidence-packet.schema.json",
    "validation_authority": "scripts/validate_evidence_packet.py",
    "task_kinds": ["dependency-check", "evidence-analysis", "repository-read", "requirement-research"],
    "finding_severity_values": ["low", "medium", "high", "critical"],
    "finding_confidence_values": ["low", "medium", "high"],
    "evidence_fields": ["source_id", "locator", "note"],
    "fact_fields": ["id", "statement", "provenance", "confidence"],
    "fact_confidence_values": ["confirmed", "inferred", "unverified"],
    "external_source_fields": ["source_id", "source_kind", "uri", "repository", "project", "revision", "retrieved_at", "license", "reuse_status", "target_applicability", "locator", "confidence", "conflicts"],
    "research_result_fields": ["status", "mode", "limitations", "uncertainty", "conflicts", "conflict_resolution"]
  },
  "execution_rules": {
    "read_only": true,
    "write_authority": "none",
    "external_mutations": "forbidden",
    "pass_parent_transcript": false,
    "may_make_decisions": false,
    "may_author_contract": false,
    "may_spawn_agents": false
  }
}
```

The real envelope must populate the policy, authorization, and economics
objects. `scripts/validate_plan.py` rejects an incomplete envelope, an
unsupported task kind, a non-positive economics decision, an over-budget
source, full-transcript access, or any write/decision authority.

## 5. Batch plan

A batch keeps the full plan shape and uses `envelope_type: "batch-plan"`:

```json
{
  "schema_version": "2.1",
  "envelope_type": "batch-plan",
  "plan_id": "payment-timeout-investigation",
  "goal": "Gather evidence for a contract.",
  "mode": "balanced",
  "configuration": {
    "id": "context-routing-defaults",
    "source": "assets/context-routing/default-config.yaml",
    "revision": 3,
    "digest": "sha256:<64-hex-digits>"
  },
  "routing": {
    "decision": "batch",
    "estimated_files": 5,
    "estimated_tokens": 7500,
    "multiple_information_boundaries": true,
    "basis": "The task crosses independent information boundaries.",
    "economics": {}
  },
  "external_research": {
    "decision": "not-required",
    "reason": "Populate this gate before approving any non-trivial proposal.",
    "status": "not-required",
    "mode": "none",
    "decision_critical": false,
    "architecture_relevant": false,
    "evidence_bar": "not-applicable",
    "target_applicability": {
      "target_versions": ["not-applicable"],
      "target_runtimes": ["not-applicable"],
      "notes": "No external target applies in this skeleton."
    },
    "source_ids": [],
    "evidence": [],
    "limitations": [],
    "uncertainty": "No external evidence has been requested in this skeleton.",
    "risk": "A real architecture proposal must reevaluate this decision.",
    "stop_conditions": ["The Planner has classified the research need."],
    "conflicts": [],
    "conflict_resolution": "No material conflict identified.",
    "fallback": "not-applicable",
    "host_capability": {
      "capability": "managed-web-research",
      "status": "not-checked",
      "mode": "none",
      "read_only": true,
      "shell_network": false,
      "external_mutations": false,
      "verified": false,
      "verification_method": "not-applicable",
      "verification": "No managed web search was requested."
    }
  },
  "plan_task_authorization": {
    "authorized": true,
    "model": "gpt-5.6-luna",
    "reasoning_effort": "max",
    "task_count": 2,
    "token_ceiling": 12000
  },
  "plan_task_policy": {
    "model": "gpt-5.6-luna",
    "reasoning_effort": "max",
    "max_concurrent_tasks": 2,
    "max_estimated_input_tokens_per_round": 12000,
    "pass_parent_transcript": false,
    "sandbox_mode": "read-only",
    "allow_writes": false,
    "allow_external_mutations": false,
    "user_visible_dispatch_notice": true,
    "per_task_approval_required": false,
    "over_policy": "user-approval-or-direct-fallback",
    "managed_web_research": {
      "capability": "managed-web-research",
      "allowed_task_kinds": ["dependency-check", "requirement-research"],
      "allowed_modes": ["cached-indexed", "live"],
      "read_only": true,
      "shell_network": false,
      "external_mutations": false,
      "unavailable_fallback": "direct-planner-or-blocked"
    }
  },
  "budget": {
    "max_subagents": 3,
    "max_input_tokens_per_task": 12000,
    "max_total_dispatched_tokens": 30000,
    "max_accidental_overlap_ratio": 0.1,
    "max_shared_source_tokens_per_task": 1200
  },
  "shared_context": {"facts": [], "constraints": [], "source_ids": []},
  "sources": [],
  "tasks": [],
  "merge": {
    "strategy": "evidence-weighted",
    "conflict_policy": "independent-review-on-material-conflict",
    "final_checks": []
  }
}
```

Each task has `task_kind`, one objective, exact `source_ids`, questions,
deliverable, evidence requirement, expansion policy, and stop conditions.
Dependency layers must not exceed two concurrent tasks under the Codex policy.
Batch packet generation retains source descriptors rather than source bytes and
does not attach the complete parent transcript.

## 6. Generated task packet

`scripts/build_task_packets.py` emits `packet_type: "plan-task"` with the
task kind, exact assigned descriptors, an explicit per-task Luna/max model
override, policy and authorization snapshots, read-only execution rules,
economics, and the following result contract:

```json
{
  "schema_version": "2.1",
  "packet_type": "subagent-result",
  "schema_ref": "assets/context-routing/evidence-packet.schema.json",
  "validation_authority": "scripts/validate_evidence_packet.py",
  "task_kinds": ["dependency-check", "evidence-analysis", "repository-read", "requirement-research"],
  "finding_severity_values": ["low", "medium", "high", "critical"],
  "finding_confidence_values": ["low", "medium", "high"],
  "evidence_fields": ["source_id", "locator", "note"],
  "fact_fields": ["id", "statement", "provenance", "confidence"],
  "fact_confidence_values": ["confirmed", "inferred", "unverified"],
  "external_source_fields": ["source_id", "source_kind", "uri", "repository", "project", "revision", "retrieved_at", "license", "reuse_status", "target_applicability", "locator", "confidence", "conflicts"],
  "research_result_fields": ["status", "mode", "limitations", "uncertainty", "conflicts", "conflict_resolution"]
}
```

For micro input, the builder emits one packet and an authenticated manifest;
for batch input, it emits one packet per task plus dependency layers. The
manifest is disposable scaffolding and is safe to overwrite only when its
generator marker and packet digests authenticate every existing output file.

## 7. Evidence Packet

An Evidence Packet uses schema `2.1`, `packet_type: "subagent-result"`, the
matching `plan_id`, `task_id`, and supported `task_kind`, plus findings with
precise source locators, reusable facts, assumptions, unknowns, and expansion
records. `partial` and `blocked` results must list missing information.
Expansion requests are proposals; `expansions_used` entries require explicit
Planner approval, and a `deny` task cannot request or use expansion.

## 8. Pre-authorized policy and compatibility

The default Codex PLAN policy is Luna/max, two concurrent tasks, 12,000
estimated input tokens per round, no complete parent transcript, read-only
permissions, no writes or external mutations, one user-visible dispatch
notice, and no per-task approval within policy. Exceeding it requires user
approval or direct fallback.

Workflow `0.7.1` uses schema/config revision `2.1`/`3`. Approved `0.7.0` and `0.6.x`
contracts and their plan/packet resources remain immutable and are continued
only with matching historical resources. Additive fields are allowed within a
version; breaking field or semantic changes require the coordinated schema,
validator, packet, and configuration revision above.
