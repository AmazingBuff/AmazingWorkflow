# Rust Scheduler Integration

Use this reference only when the host scheduler is implemented in Rust.

## Data boundary

Keep planning, source materialization, model invocation, and merging as separate components:

```text
Planner -> OrchestrationPlan
Validator -> ValidationReport
PacketBuilder -> Vec<TaskPacket>
SourceProvider -> Vec<MaterializedSource>
AgentRunner -> ResultPacket
Merger -> MergeReport
```

This separation prevents the planner from reading and embedding complete files.

## Minimal serde models

The complete schema contains more optional fields. These minimal structures illustrate the boundary:

```rust
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::BTreeMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SourceRef {
    pub id: String,
    pub uri: String,
    pub selector: Value,
    pub estimated_tokens: u64,
    pub purpose: String,
    #[serde(default)]
    pub summary: Option<String>,
    #[serde(default)]
    pub content_hash: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExpansionPolicy {
    pub mode: String,
    pub max_additional_tokens: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskDef {
    pub id: String,
    pub agent_role: String,
    pub objective: String,
    #[serde(default)]
    pub dependencies: Vec<String>,
    #[serde(default)]
    pub source_ids: Vec<String>,
    #[serde(default)]
    pub questions: Vec<String>,
    pub deliverable: String,
    pub evidence_required: bool,
    pub intentional_overlap: bool,
    #[serde(default)]
    pub capabilities: Vec<String>,
    pub allowed_expansion: ExpansionPolicy,
    #[serde(default)]
    pub stop_conditions: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OrchestrationPlan {
    pub schema_version: String,
    pub plan_id: String,
    pub goal: String,
    pub mode: String,
    pub budget: Value,
    pub shared_context: Value,
    pub sources: Vec<SourceRef>,
    pub tasks: Vec<TaskDef>,
    pub merge: Value,
    #[serde(default)]
    pub assumptions: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MaterializedSource {
    pub source_id: String,
    pub content: String,
    pub actual_tokens: Option<u64>,
    pub resolved_version: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskPacket {
    pub schema_version: String,
    pub packet_type: String,
    pub plan_id: String,
    pub task_id: String,
    pub parent_goal: String,
    pub mode: String,
    pub agent_role: String,
    pub objective: String,
    pub context: Value,
    pub assigned_sources: Vec<SourceRef>,
    pub dependencies: Vec<String>,
    pub upstream_context: BTreeMap<String, Value>,
    pub response_contract: Value,
}
```

Use strongly typed nested structures after the contract stabilizes. Keeping a few fields as `serde_json::Value` during initial integration makes schema evolution easier.

## Adapter traits

Use application-specific error types in production. The following shape keeps the interfaces independent:

```rust
use async_trait::async_trait;

#[async_trait]
pub trait SourceProvider: Send + Sync {
    async fn materialize(
        &self,
        source: &SourceRef,
    ) -> anyhow::Result<MaterializedSource>;
}

#[async_trait]
pub trait AgentRunner: Send + Sync {
    async fn run(
        &self,
        packet: &TaskPacket,
        sources: &[MaterializedSource],
    ) -> anyhow::Result<serde_json::Value>;
}
```

The runner should build prompts from the packet and source fragments. It should not receive the parent agent's transcript.

## Dispatch algorithm

1. Validate the plan before spawning tasks.
2. Build a task graph from `dependencies`.
3. Select all dependency-free tasks that fit the current concurrency and token budget.
4. Materialize only their assigned sources.
5. Invoke the selected agents concurrently.
6. Validate each result packet.
7. Convert upstream results into compact facts for dependent tasks.
8. Handle expansion requests within the declared policy.
9. Continue until all reachable tasks finish or are blocked.
10. Merge results using the plan's conflict policy.

Use a semaphore or bounded task set so `max_subagents` is not confused with unbounded runtime concurrency.

## Dependency summaries

Do not copy an entire upstream result into every dependent packet. Extract only:

```json
{
  "task_id": "task-parser",
  "status": "complete",
  "facts": [
    {
      "statement": "The parser normalizes timestamps to UTC before validation.",
      "provenance": ["src-parser-time"]
    }
  ],
  "unknowns": []
}
```

Preserve provenance so a downstream finding can be traced to original material.

## Source version checks

When a source provider can return a hash or version:

1. Compare it with `content_hash` in the descriptor.
2. Reject or re-plan stale packets when the version differs.
3. Store the resolved version in the result packet.

This avoids merging findings produced from different repository states.

## Practical CLI layout

A simple project layout:

```text
src/
  planner.rs
  validator.rs
  packet.rs
  source_provider.rs
  runner.rs
  scheduler.rs
  merger.rs
schemas/
  orchestration-plan.schema.json
config/
  orchestrator.yaml
```

Copy `assets/orchestration-plan.schema.json` and `assets/default-config.yaml` into the corresponding directories, then adapt the opaque `uri` and `selector` fields to the application's file or object APIs.
