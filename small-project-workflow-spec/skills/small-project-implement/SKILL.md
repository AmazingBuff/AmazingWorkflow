---
name: small-project-implement
description: Implement a confirmed small-project task packet or a bounded review/test repair packet without making new product or architecture decisions. Use only in IMPLEMENTING, REVIEW_FIX, or TEST_FIX when the packet includes a confirmed spec version, baseline, scope, allowed mutations, rules, acceptance criteria, and required evidence.
---

# 小项目编码执行

1. 验证任务包包含 `task_id`、`iteration_id`、`mode`、`baseline`、`confirmed_spec_version`、范围、允许修改、适用规则、验收条件和返回证据。
2. 通过当前 Harness 的原生 skill loader 读取 `small-project-code-contract`。Python 使用 `small-project-python-rules`；C++ 使用 `small-project-cpp-rules`。
3. 既有项目遵循仓库规则和相邻第一方模式；绿地项目采用最小结构。
4. 按任务包进行最小、模块化修改。不得自行改变需求、架构、公共接口、依赖、通过条件或范围。
5. 每完成一个逻辑单元，运行最窄可用的格式化、静态检查、构建或 smoke；不要替代正式测试阶段。
6. 修复模式仅解决打包问题及必要影响范围，不顺便清理无关代码。
7. 发现任务包矛盾、需要新依赖或需要扩大公共契约时停止并返回强模型。

返回变更文件、行为摘要、实际命令与结果、未验证项、偏离或阻塞、以及供 Review 使用的基线。不要自我 Review 或宣称未运行的验证通过。
