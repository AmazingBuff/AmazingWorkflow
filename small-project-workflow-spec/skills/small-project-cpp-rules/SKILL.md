---
name: small-project-cpp-rules
description: Apply the workflow's self-contained C++ and CMake engineering standard when planning, implementing, reviewing, testing, or migrating a small C++ project. Covers project inspection, architecture, C++ style, target-based CMake, ownership, tests, validation, and Python-to-C++ migration without relying on an external skill.
---

# Small Project C++/CMake Rules

本 skill 是 workflow 内置且自包含的 C++/CMake 规范。不要读取、触发或依赖环境中的 `cpp-cmake-engineering-rules`；所有权威内容均在本目录。

同时遵守已通过当前 Harness 原生 loader 加载的 `small-project-code-contract`。冲突时按 workflow 的全局优先级裁决；本 skill 的绿地默认值只在仓库没有更高优先级规则时生效。

## 执行流程

1. 读取任务包和仓库内贡献指南、CMake、presets、包管理、格式化、静态检查、CI 与测试入口。
2. 排除 vendor、generated、build、install 和外部依赖，只从第一方代码提取项目惯例。
3. 判断既有项目适配或绿地设计。既有项目保持接口、工具链和局部一致；绿地采用最小结构。
4. 明确最小行为、模块、调用链、公共契约、所有权、错误模型和依赖方向，再决定抽象。
5. 按任务包做手术式修改；不得借功能改动全仓格式化、搬目录或升级工具链。
6. 实现阶段仅运行最窄构建或静态检查；正式测试的时机、判据与门禁由 `small-project-test-plan` 决定。

需要快速识别项目现状时，从本 skill 目录运行：

```text
python scripts/inspect_project.py <project-root>
python scripts/inspect_project.py <project-root> --format json
```

该脚本只收集证据，不判定风格，也不修改项目。

## 按任务读取内置规范

以下文件是本 workflow 的内置规范，不是外部引用：

- 创建项目、模块、接口、数据流、抽象或资源生命周期：读取 [project-architecture.md](references/project-architecture.md)。
- 编写、修改或 Review C++：读取 [cpp-style.md](references/cpp-style.md)。
- 修改 target、依赖、生成步骤、安装、导出或 presets：读取 [cmake-style.md](references/cmake-style.md)。
- 为测试规划提供 C++ 检查项或执行已批准测试：读取 [testing-and-validation.md](references/testing-and-validation.md)。
- 局部约定冲突或计划迁移：读取 [decision-policy.md](references/decision-policy.md)。

不得只依据本页摘要执行涉及上述领域的任务；必须读取对应内置参考。

## 核心规则

- 公共契约与私有实现分离；依赖由易变外层指向稳定内层。
- 只为真实变化轴、外部边界或可验证替身建立抽象；单一路径直接实现。
- 默认值语义、RAII 和唯一所有权；`shared_ptr` 只用于真实共享生命周期，裸指针/引用表达借用。
- 运行时替换使用小接口或 callable；编译期策略才使用 concepts、traits 或 policy。
- CMake 使用 target-based 命令、最窄正确作用域、单一依赖来源和 binary-tree 生成物。
- 公共 API 不泄漏私有实现、具体后端或不必要的外部库类型。
- 便利重载转发至一个 canonical implementation，不复制算法、转换或验证。
- 每个新外部信任边界只验证一次；可信内部不重复输入验证，但保留 assertion、生命周期、并发、内存、ABI 和运行状态检查。

## 绿地最小结构

```text
CMakeLists.txt
CMakePresets.json        # 按需
cmake/                   # 按需
include/<project>/       # 仅稳定公共库 API 需要
src/
apps/ 或 tools/          # 按需
tests/
```

只有组件可独立构建、测试或复用时才拆独立 target。命名、格式、include、模板、安装与平台细则以内部参考为准。

## Python 向 C++ 迁移

将迁移视为契约迁移而非逐行翻译。先冻结 schema、dtype、shape、单位、布局、错误语义、随机性与容差，再 profile 证明迁移必要性；只迁移受约束计算核。建立 C++ target/API 与 golden differential tests，通过等价性、性能和资源验证后才切换唯一权威实现。按环境选择标准容器/`span`、Eigen 或 xtensor，以及 CLI、C ABI、pybind11 或 nanobind。

## 完成证据

返回变更、关键决策、实际命令与原始结果、未运行项及剩余风险。语言 skill 只提供检查项，不自行打开 `G4`、`G6` 或交付门禁。
