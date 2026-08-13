---
name: small-project-report
description: Generate a concise delivery report from approved plans, closed review findings, test evidence, and explicit user acceptance.
---

# Small Project Report

由执行等级模型在用户明确验收后生成事实汇总。报告不能创造新结论、补写不存在的测试或推断用户未表达的满意度。

## 允许的事实来源

- 已确认的需求、方案与技术决策；
- 实际文件差异和版本基线；
- 已关闭的 Review 问题；
- 测试命令、结果与证据；
- 明确的用户验收记录。

来源之间矛盾、存在未关闭问题或证据缺失时，停止报告并交强模型裁决。

## 报告结构

```markdown
# I01 交付总结

## 达成的目的
...

## 已实现功能
- ...

## 关键技术与依赖
- ...

## Review 与测试
- Review: G4 clear, ...
- Tests: G6 pass, I01-EVD-...

## 使用方式
...

## 已知限制与未验证项
...

## 验收与版本
- UAT: I01-UAT-001 accepted
- Delivery baseline/version: ...
```

报告完成后封存本迭代的基线、追踪矩阵和验收记录，进入 `DLV-01`。后续需求追加为新迭代，不改写已交付历史。
