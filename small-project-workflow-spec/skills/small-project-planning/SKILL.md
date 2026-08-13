---
name: small-project-planning
description: Convert a user-approved small-project solution into a proportional module plan, file scope, traceability matrix, rollback baseline, and bounded task packets that an execution model can implement without making architecture decisions. Use only after solution confirmation and before IMPLEMENTING.
---

# Small Project Planning

该阶段由强模型执行。把已确认的需求与技术路径变成可执行计划；不写产品代码。

## 进入条件

必须有已批准的项目目的、范围、非目标、技术与依赖决策、验收标准、风险和回滚策略。用户“完全遵循安排”的授权可以代替方案确认记录，但不能代替外部或破坏性操作授权。

## 规划流程

1. 捕获迭代基线：commit、文件清单或可恢复 artifact；不得覆盖已交付历史。
2. 按真实职责划分最少模块，明确输入输出与依赖方向；禁止为模板创建空层级。
3. 选择 `small-project-code-contract` 与对应语言规则；Python 使用 `small-project-python-rules`，C++ 使用 `small-project-cpp-rules`。
4. 把每条需求和验收标准映射到任务、文件范围、Review 意图和测试意图。
5. 将任务拆成一个写 Agent 可顺序完成的有界任务包；低等级 Agent 不应再需要选择架构、公共接口或新依赖。
6. 定义并发策略。小项目默认单写者；只读研究或不重叠测试才可并发。
7. 在存在数据、部署或外部状态变化时，写明精确回滚与授权点。

## 任务包

```yaml
task_id: I01-TASK-001
iteration_id: I01
mode: initial # initial | review-fix | test-fix
baseline: <commit-or-artifact-id>
confirmed_spec_version: <version>
objective: <single bounded outcome>
in_scope: []
out_of_scope: []
files_or_modules: []
allowed_mutations: []
inputs: []
applicable_rules: []
acceptance_criteria: []
test_intent: []
required_evidence: []
return_contract: []
stop_conditions: []
```

## 追踪矩阵

每条验收标准至少一行：

```text
Iteration | Objective/REQ | AC | Decision | Task/files | Review/status | Test | Evidence | UAT | Delivery
```

每个需求至少一个 AC；每个任务指向需求/AC；每个 AC 至少一个自动测试或明确人工证据。计划完整后开放 `G2 IMPLEMENTATION_READY`。
