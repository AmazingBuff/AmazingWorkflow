---
name: small-project-feedback-analysis
description: Analyze failed acceptance feedback, identify root cause, and produce a scoped fix or replanning packet for the small-project loop.
---

# Small Project Feedback Analysis

该阶段由强模型执行。先确认反馈属于缺陷、测试或环境问题、需求歧义还是新需求，再决定回环位置；不得直接猜修复。

## 分析流程

1. 将用户观察与关联的 `REQ`、`AC`、测试和证据对齐。
2. 用户给出明确问题点时，从该差异向输入、状态、转换、输出和直接调用链溯源。
3. 用户只说“有问题”时，先询问最小必要信息：实际结果、期望结果、复现条件或可视化中的具体差异。
4. 复现并定位根因；把症状与根因分开记录。
5. 决定最窄回环：
   - 违反已确认 AC 的产品缺陷：`FIX-01 -> REV-01 -> TPLAN-01/TEST-01 -> UAT-01`。
   - 测试配置或环境问题：修测试任务包并回 `TPLAN-01`。
   - 已确认方案无法满足要求：回 `SOL-01 -> CONF-01`。
   - 新行为：登记变更并回 `CHG-01 -> REQ-01`。
6. 将修复问题包交给执行模型；本阶段不直接编码。

交付前 UAT 缺陷保留当前迭代。交付后缺陷不得重开旧迭代：建立下一 maintenance 或 mixed iteration，在新迭代登记 DEF 并引用来源 AC；若根因修复不改变既定行为、公共契约、架构或依赖，转强模型规划后实现；否则先回方案确认。

同一问题连续两轮无实质进展时，由强模型重新做根因分析并调整方案；第三次仍是同一外部阻塞时请求用户决策。只要有新证据或进展，不设置机械循环上限。

## 修复或重规划包

```text
Finding: I01-DEF-001
Related: I01-REQ-..., I01-AC-..., I01-TST-..., I01-EVD-...
Observed: ...
Expected: ...
Root cause: ...
Fix scope/files: ...
Must preserve: ...
Regression checks: ...
Return stage: REV-01 | SOL-01 | TPLAN-01 | REQ-01
```
