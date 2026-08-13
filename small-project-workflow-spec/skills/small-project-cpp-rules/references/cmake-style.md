# CMake 工程规则

## 目录

- 适配原则
- 根文件编排
- 目标与作用域
- 源文件与目录
- 依赖
- 平台与生成步骤
- 安装与导出
- Presets
- 验证

## 适配原则

先读取现有 `CMakeLists.txt`、`CMakePresets.json`、toolchain、包管理清单和 CI。保持受支持的 CMake 版本、生成器、平台和目标名称；不要把工具链升级夹带在功能修改中。

绿地项目应显式选择：

- 满足所用 CMake 功能且受目标环境支持的最低版本。
- 满足代码与依赖的最低 C++ 标准。
- 实际支持的生成器、编译器和平台矩阵。
- 库类型、依赖获取方式、安装需求和测试入口。

## 根文件编排

按适用项组织：

1. `cmake_minimum_required`
2. `project`
3. 用户选项和 feature flags
4. toolchain/平台能力检测
5. 依赖发现
6. 目标定义
7. 目标 sources、includes、features、definitions 和 links
8. 生成步骤与平台适配
9. tests、examples、install 和 export

顺序服务于可读性；依赖必须先定义时做最小调整。

```cmake
cmake_minimum_required(VERSION <supported-minimum>)

project(
    project_name
    LANGUAGES CXX
)

add_library(project_name)

target_sources(
    project_name
    PRIVATE
    src/component.cpp
)

target_include_directories(
    project_name
    PUBLIC
    "$<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>"
    "$<INSTALL_INTERFACE:include>"
)

target_compile_features(
    project_name
    PUBLIC
    cxx_std_<required-standard>
)
```

## 目标与作用域

- 使用 `target_*` 命令，避免目录级 `include_directories`、`link_libraries`、`add_definitions`。
- 每个目标只定义一次；子目录只能扩展已知目标或定义独立目标。
- 选择最窄正确作用域：
  - 公共头需要的依赖使用 `PUBLIC`。
  - 仅实现需要的依赖使用 `PRIVATE`。
  - header-only 消费需求使用 `INTERFACE`。
- 不用全局编译选项解决单个目标的问题。
- 为库提供稳定 namespaced alias 时，可使用 `add_library(Project::Target ALIAS target)`。
- 目标名、输出名和导出名是不同概念；不要为视觉统一破坏消费方。

## 源文件与目录

- 小型或稳定目标优先显式列出 sources，便于审查和可靠重新配置。
- 既有项目使用 glob 时保持一致；新 glob 使用 `CONFIGURE_DEPENDS` 并限制到第一方目录。
- 公共头、私有头和实现文件在 `target_sources` 中按可见性组织。
- 平台互斥实现通过条件分支或独立对象库选择，避免同时编译。
- 生成文件写入 binary tree，不污染源码树。
- 路径使用引号和 CMake 路径语义，不硬编码本机绝对路径。

## 依赖

- 优先消费上游导出的 CMake target，而不是手工拼 include 和 library 路径。
- 依赖可由 `find_package`、项目包管理器或受控源码获取提供；一个依赖只设一个权威来源。
- 锁定版本时记录兼容范围和更新机制。
- 外部依赖使用 `SYSTEM` include 仅用于抑制其诊断，不掩盖第一方警告。
- 私有依赖不应泄漏到安装接口。
- 复制运行时文件时使用 target-aware generator expressions，不硬编码输出目录。

## 平台与生成步骤

- 把平台判断集中在构建或适配层，不散落到无关目标。
- 用 capability check 优先于仅判断操作系统名称。
- 编译器特定选项放在明确条件中，并说明它解决的兼容问题。
- 自定义命令必须声明 `OUTPUT`/`BYPRODUCTS`、`DEPENDS` 和消费目标。
- 代码生成工具与运行时库使用独立目标；生成目录通过目标作用域传递。
- 多配置生成器不依赖 `CMAKE_BUILD_TYPE`；使用 generator expressions 或 preset 配置。

## 安装与导出

仅在目标需要被外部消费时增加安装规则：

- 安装公共头、库、运行时文件和 package config。
- 通过 build/install interface 分离源码路径与安装路径。
- 共享库显式管理符号可见性和导出宏。
- 导出的 target 使用稳定 namespace，避免暴露构建树内部目标。
- 用安装后的最小消费项目验证 package，而不只验证源码树链接。

## Presets

- presets 表达受支持工作流，不枚举未经验证的编译器组合。
- 将生成器、toolchain 和公共 cache 变量放入隐藏 base preset。
- debug、release 和其他配置直接继承共同 base，避免配置间意外继承诊断或优化选项。
- binary/install 目录包含 preset 名，避免配置互相覆盖。
- 个人本机路径放入 `CMakeUserPresets.json`，不提交到共享 preset。
- schema 版本与项目最低 CMake 版本兼容。

## 验证

按项目支持的工作流运行：

```text
cmake --preset <configure-preset>
cmake --build --preset <build-preset>
ctest --preset <test-preset> --output-on-failure
```

没有 presets 时使用明确的 `-S`、`-B`、generator 和 toolchain 参数。至少验证一个受支持配置；涉及平台、编译选项或公开安装接口时扩大到对应矩阵。不要声称未运行的编译器、SDK 或配置已通过。
