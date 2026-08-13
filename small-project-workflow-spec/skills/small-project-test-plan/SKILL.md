---
name: small-project-test-plan
description: Plan a small project's tests from confirmed acceptance criteria or evaluate raw test-run evidence and classify failures. Use only after REVIEW_CLEAR in TEST_PLANNING, or in TEST_EVALUATING with the immutable plan and execution artifacts; this strong-model skill owns pass criteria and result judgment.
---

# 小项目测试规划与判定

## Plan 模式

1. 为每条验收条件建立至少一个自动测试或明确人工证据。
2. 定义环境、命令、数据、期望结果、容差、可视化产物、原始证据格式和失败分类。
3. 未提供数据时，至少覆盖 import/configure、启动或构建，以及一条最小代表路径；只可证明可运行。
4. 提供数据和期望时，按用户要求与确认容差判断基本符合。
5. 提供数据但没有期望时，先定义结构、数量、范围、单位、缺失值、确定性和完整性 oracle；无法定义时标记正确性未验证并询问用户。
6. 形成不可变测试计划，交已加载 `small-project-test-run` 的执行 Agent 执行。

## Evaluate 模式

读取所有命令、退出码、日志、实际值和可视化产物，分类为：

- `pass`：计划内测试全部满足判据。
- `product-defect`：生成 `test-fix` 包，修复后必须局部 Review，再运行失败项、影响项和最小 smoke。
- `test-or-environment`：修订测试计划或环境后重测，不修改产品代码。
- `requirement-ambiguity`：返回需求/方案阶段澄清。
- `unknown`：先诊断；不允许无变化重复运行。

只有本 skill 可以判定 `G6 TEST_PASS` 是否通过。
