# Coding Rules Components（SPW 规范组合适配版）

本目录存放 lightweight-coding-workflow 实现阶段使用的编码规范组件。它们是
`small-project-workflow-spec`（下称 SPW）三个规范 skill 的**组合适配副本**：
仅把 SPW 生命周期词汇映射到本框架的两阶段编排，**代码规则本身未做任何修改**。
SPW 原始版本保持不动；组合工作流只消费本目录版本。

## 来源与同步

- 来源基线：`small-project-workflow-spec` @ git `5fb6ec0`（已包含 cpp-style.md
  命名表/auto 规则修订与 SKILL.md 预编译头规则）。
- SPW 上游更新时需重新对照本目录，并同步维护下方改动清单。

## 组件清单

| 目录 | 来源 | 用途 |
|---|---|---|
| `small-project-code-contract/` | 同名 SKILL.md | 跨语言工程契约：模块、函数设计、输入边界验证、依赖与变更范围 |
| `small-project-cpp-rules/` | 同名目录 | C++/CMake 规范；`references/` 五份细则与 `scripts/inspect_project.py` 原样携带 |
| `small-project-python-rules/` | 同名 SKILL.md | Python 工程结构与编码规范 |

有意未携带：各 SPW skill 的 `agents/openai.yaml`（Codex 专用 agent 定义，与本框架无关）。

## 相对源版的改动（仅编排词汇）

| 文件 | 改动点 |
|---|---|
| `small-project-code-contract/SKILL.md` | “任务包”→“实现契约”；“回到强模型规划与用户确认”→“停止实现并经 Planner 与用户确认新契约修订版”；“语言 skill”→“语言规范” |
| `small-project-cpp-rules/SKILL.md` | “任务包”→“实现契约”（2 处）；`small-project-test-plan` 引用改为“由实现契约的 Acceptance criteria 与 Verification 章节决定”；`G4/G6` 门禁改为中性表述；“Harness 原生 loader 加载”→“随附提供”；“workflow 内置”→“lightweight 编排框架内置” |
| `small-project-cpp-rules/references/testing-and-validation.md` | 首段同上口径：检查清单服务于契约 Verification；“`G6 TEST_PASS`”改为中性表述 |
| `small-project-python-rules/SKILL.md` | “Harness 原生 loader 加载”→“随附提供”；“workflow 内置”→“lightweight 编排框架内置” |

## 使用方式

这些文件**不作为独立 skill 安装**。实现契约的 Applicable coding rules 一节列出
具体文件路径，实现 worker 以普通文档方式读取；`small-project-cpp-rules`
内部的相对引用（references/、scripts/）以本目录为基准解析。

## 优先级

规则冲突时遵循 code-contract 的全局优先级；规范绿地默认值让位于仓库既有约定；
测试时机、验收判定与交付门禁属于实现契约和用户，规范组件只提供检查项。
