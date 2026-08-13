---
name: small-project-requirements
description: Normalize and validate an initial or post-delivery requirement for a small project, research comparable patterns when useful, evaluate feasibility and impact, recommend a technical path, define acceptance criteria, and obtain user confirmation. Use only in REQUIREMENTS or CHANGE_REQUIREMENTS with mode initial or change.
---

# 小项目需求规范

## 输入

接收 `mode: initial | change`、用户原始需求、当前基线、既有约束、项目目的和用户是否已明确完全授权。

## 处理

1. 读取能够从仓库确定的现状，不询问可自行查明的问题。
2. 说明项目目的、使用者、目标行为、输入输出、限制和非目标。
3. 需要时研究同类项目，从产品形态、交互、结构或算法获取灵感；记录借鉴模式和来源，不复制未授权代码或资产。
4. 判定技术、平台、数据、依赖、许可、性能、回滚和实施可行性。
5. 比较候选路径并推荐一条路径，解释顺序和取舍。
6. 可视化默认优先 Python；存在经验证的性能、原生集成、部署或硬件约束时支持 C++ 或 Python→C++ 计算核迁移。
7. 第三方库只作方案建议，列明用途、替代项、许可、体积和平台代价。
8. 定义可观察、可判定的验收条件。新需求模式还要分析接口、数据、依赖、文件、回归和测试影响。
   对数据可视化项目，确认数据字段/轴/系列映射、输入格式与缺失值口径、交互行为和导出尺寸/格式；不得把这些决策留给实现 Agent。
9. 将方案交给用户确认；仅当用户明确完全遵循安排时记录授权并代为确认。该授权只免除方案确认，不免除外部写入、破坏性操作或最终验收。

## 输出

输出 `PURPOSE`、`CURRENT`、`PATH`、`FEASIBILITY`、`TECH`、`SCOPE`、`AC`、`TEST-BASIS`、风险、回滚和 `DECISION`。

若不可行，说明原因和替代路径。若信息不足且会改变方案，询问用户。未经确认不得生成实现任务包。
