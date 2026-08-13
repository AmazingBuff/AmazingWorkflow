---
name: small-project-acceptance
description: Present verified small-project results for user acceptance and route acceptance, defects, mixed feedback, or new requirements correctly.
---

# Small Project Acceptance

在 Review 与测试门禁通过后，把可运行结果和必要的可视化证据交给用户验收。

## 验收包

只展示已验证事实：本迭代目的、实现行为、运行方式、关键测试结果、可视化或产物路径、已知限制，以及需要用户判断的具体事项。不要用内部实现细节淹没验收目标。

## 用户反馈分类

- 明确通过：记录 `Ixx-UAT-xxx = accepted`，开放 `G7 UAT_ACCEPTED`，进入报告与交付。
- 当前要求存在问题：转 `small-project-feedback-analysis`；完成根因、修复、局部复审和重测后重新验收。
- 要求新的行为：创建 `Ixx-CHG-xxx`，若旧迭代已交付则创建下一迭代，重新走可行性、方案确认、实现、Review、测试和验收。
- 混合反馈：把违反已确认验收标准的部分记为缺陷，把新增行为记为新需求，分别追踪。
- 不明确：提出最少且具体的问题，获取可观察的差异或期望；不得仅凭沉默推定通过。

“完全遵循你的安排”只可免除方案确认，不代表自动验收，也不授权外部或破坏性操作。

若反馈发生在已经 `DELIVERED` 的版本，旧迭代只读：纯缺陷建立下一 maintenance iteration；纯新行为建立 change iteration；混合反馈默认建立一个 mixed iteration，并在新迭代用独立 DEF/CHG ID 引用旧 AC。含新行为时必须重新确认方案。

## 验收记录

```text
UAT: I01-UAT-001
Iteration: I01
Evidence shown: I01-EVD-...
User decision: accepted | issue | new_requirement | mixed | awaiting
User feedback: ...
Next state: RPT-01 | FIX-01 | CHG-01 | AWAITING_UAT
```

只有用户明确通过时才能进入 `DELIVERED`；用户未回复时保持 `AWAITING_UAT`。
