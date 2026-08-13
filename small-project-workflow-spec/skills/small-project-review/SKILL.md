---
name: small-project-review
description: Independently review a confirmed small-project iteration for logic errors, regressions, unauthorized scope, and compliance, or re-review a bounded repair delta. Use only in REVIEWING with the confirmed spec, iteration baseline, diff, applicable language rules, review mode, and prior finding IDs.
---

# 小项目 Code Review

使用独立强模型和只读权限。读取确认版 spec，并通过当前 Harness 的原生 skill loader 加载 `small-project-code-contract` 和对应语言规则。

## 范围

- `initial`：审查本迭代全部 diff 和直接受影响的契约。
- `focused`：只审查修复 diff、原 finding、直接调用者/被调用者、相关接口和测试。
- 可以读取其他代码理解上下文，但不得重审无关历史代码。
- 公共 API/ABI、数据格式或构建配置发生变化时可扩大直接影响范围，并说明原因。

## 检查

优先检查逻辑错误、需求不一致、回归、资源/错误路径、规范违反、未授权依赖或范围扩张，以及会阻止验证的测试缺口。无规范依据的风格偏好标记为 non-blocking，不得阻断门禁。

每个可执行问题输出：

```yaml
finding_id: I01-REV-001
severity: blocker
location: path:line
observed_behavior: ""
evidence: ""
expected_behavior: ""
required_change: ""
affected_scope: []
verification: []
status: open
```

将 open findings 打包给执行 Agent。只有存在修复证据时关闭 ID。通过条件是 `open actionable findings == 0`。同一问题连续两轮无实质进展时重新做根因和方案分析；第三次仍是相同外部阻塞时请求用户决策，不盲目循环。
