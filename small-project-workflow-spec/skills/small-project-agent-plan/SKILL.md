---
name: small-project-agent-plan
description: Establish the model and Agent role map for a small-project iteration before requirements or implementation begin. Use only when the workflow phase is AGENT_PLANNING or when a configured model becomes unavailable and the strong decision role must explicitly remap it.
---

# 小项目 Agent 编排

1. 枚举当前实际可用的模型和推理强度；不要仅按记忆假设可用性。
2. 将规划、可行性、技术决策、Review、测试规划和结果判定分配给 `decision_strong`；Review 必须使用独立、只读的 `review_strong_isolated`。
3. 将实现、修复和测试执行分配给 `execution_bounded`，将报告分配给 `report_bounded`。从当前 Harness 的 adapter 清单读取实际模型与推理档位，不在本 skill 内猜测 provider/model ID。
4. 强模型不可静默降级；不可用时向用户说明。执行模型回退也必须记录。若宿主不能提供独立上下文、角色级模型或只读 Review，输出 `CAPABILITY_UNSATISFIED` 并停止推进门禁。
5. 使用独立强模型进行 Review，避免实现 Agent 自审。
6. 小项目默认顺序写入；只并发互不依赖的只读探索、测试或审计。
7. 定义任务包字段和每个 Agent 的写权限、禁止决策、返回证据及停止条件。

输出 `model_roles`、各阶段 Agent、回退策略和并发策略。不要在本阶段规划产品方案或修改代码。
