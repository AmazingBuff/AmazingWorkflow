---
name: small-project-workflow
description: Orchestrate a small software project from a new or changed requirement through feasibility, user-confirmed planning, bounded implementation, independent code review, testing, user acceptance, reporting, and later iterations. Use when starting, continuing, delivering, or adding a post-delivery requirement to a small Python or C++ project.
---

# 小项目工作流总控

## 权威规范

优先读取本 skill 内 `references/SPEC.md`；源套件开发态若该文件尚未生成，才读取本 skill 目录向上两级的 `SPEC.md`。将读取结果作为生命周期、门禁、Agent 分工和语言规则的唯一流程契约。两个位置都不存在，或安装清单中的 spec 哈希不匹配时，停止状态推进并报告套件安装不完整；不得根据记忆补写规范。总控只维护状态、检查门禁和路由下一阶段；不要替代阶段 skill 编码、Review 或执行测试。

下文“调用”表示通过当前 Harness 的原生 skill loader 加载指定名称，再按其契约执行：Codex 使用 skill 调用；OpenCode 使用原生 `skill` tool；Pi 使用 `/skill:<name>` 或等价 loader。禁止仅复述名称而不加载正文。

## 初始化

1. 识别项目是绿地还是既有项目，读取项目规则和当前基线。
2. 为初次项目建立 `I01`；交付后的新增或变更范围建立下一 `Inn`。
3. 显式调用 `small-project-agent-plan` 建立本迭代角色映射。
4. 显式调用 `small-project-requirements`，传入 `mode: initial | change`。
5. 在用户确认方案前停止，不派发实现；用户已明确完全授权时记录该授权后继续。
6. 确认后显式调用 `small-project-planning` 生成追踪矩阵与任务包，再进入实现。

## 路由

按当前 `phase` 只调用一个下一阶段 skill：

| Phase | Skill | 通过后 |
|---|---|---|
| `AGENT_PLANNING` | `small-project-agent-plan` | `REQUIREMENTS` |
| `REQUIREMENTS` / `CHANGE_REQUIREMENTS` | `small-project-requirements` | `AWAITING_CONFIRMATION` |
| `PLANNING` | `small-project-planning` | `IMPLEMENTING` |
| `IMPLEMENTING` / `REVIEW_FIX` / `TEST_FIX` | `small-project-implement` | `REVIEWING` |
| `REVIEWING` | `small-project-review` | 修复或 `TEST_PLANNING` |
| `TEST_PLANNING` / `TEST_EVALUATING` | `small-project-test-plan` | 执行、修复或验收 |
| `TEST_RUNNING` | `small-project-test-run` | `TEST_EVALUATING` |
| `USER_ACCEPTANCE` | `small-project-acceptance` | 分析、报告或新迭代 |
| `FEEDBACK_ANALYSIS` | `small-project-feedback-analysis` | `IMPLEMENTING` |
| `REPORTING` | `small-project-report` | `DELIVERED` |

实现或 Review 时，同时调用 `small-project-code-contract` 和对应语言规则：Python 使用 `small-project-python-rules`；C++ 使用 `small-project-cpp-rules`。

## 门禁

- 没有确认版需求、范围和验收条件，不进入实现。
- 没有完整任务包，不派发执行 Agent。
- Code Review 存在任何未关闭 actionable finding，不进入测试。
- 测试没有通过强模型判定，不进入用户验收。
- 用户没有明确接受，不生成完成报告或标记交付。
- 需求或验收条件变化时，使后续实现、Review 和测试结论失效。
- 代码变化时，使受影响的 Review 和测试结论失效。

## 反馈分类

- 已确认行为没有实现：保留当前 iteration，进入缺陷溯源。
- 增加或改变确认范围：只有交付后才建立新 iteration，重新做可行性、影响分析和用户确认。
- 交付后发现旧 AC 缺陷：旧 iteration 保持只读，建立下一 maintenance iteration；新缺陷 ID 引用旧 AC，根因分析后再规划修复。
- 交付后同时包含旧缺陷与新行为：建立下一 mixed iteration，分别追踪 DEF 与 CHG；新行为方案确认前不得实现任何合并任务包。
- 无法区分或用户没有具体问题点：停在验收阶段并询问，不猜测、不编码。

## 状态

在用户允许时维护 `.small-project/state.yaml`，至少记录 `iteration_id`、`phase`、`baseline`、`confirmed_spec_version`、模型映射、Review/测试轮次、门禁和工件引用。否则在当前任务上下文维护等价状态。

禁止跳过状态、无变化重跑失败测试、并行写同一工作树或让执行模型自行改变设计。
