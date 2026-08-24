---
name: skse-plugin-template
description: Scaffold and maintain a new Skyrim SKSE plugin (C++ DLL) with multi-runtime SE/AE/VR support via CommonLibSSE, based on the proven structure of the CorpseESP and FollowerSummonAllyFix projects. Run scripts/scaffold.py to generate a new plugin, or follow the conventions to extend an existing one. Complies with the small-project-cpp-rules component bundled in this skill (assets/coding-rules).
---

# SKSE Plugin Template (multi-runtime Skyrim)

本 skill 提供一套经过 CorpseESP 与 FollowerSummonAllyFix 两个真实项目验证的
**Skyrim SKSE 插件工程模板**，支持同一份 DLL 在 Skyrim **SE / AE / VR** 多运行时上工作
（CommonLibSSE 多运行时机制），并内建一套可选的常用功能模块（INI 配置、热键、D3D11
Present 钩子、vtable 钩子、事件监听）。

它同时遵守本 skill 内置的编码规范组件（随套件分发，位于本 skill 目录的
`assets/coding-rules/`）：

- 跨语言契约：`small-project-code-contract/SKILL.md`
- C++/CMake 规范：`small-project-cpp-rules/SKILL.md`

（绿地默认值、target-based CMake、显式 sources、4 空格/Allman/east const 等）。冲突时按全局优先级裁决。

## 何时使用

- 用户要求"新建/生成一个 Skyrim SKSE 插件（DLL）项目"或"做一个 Skyrim mod（C++ 插件）"。
- 用户要求按多运行时（SE/AE/VR）方式搭建 SKSE 插件骨架。
- 需要在既有插件中新增 INI 配置、热键、Present 渲染、vtable 钩子或事件监听模块。

## 快速开始：脚手架

从本 skill 目录运行（或让 Agent 代为运行）：

```text
python scripts/scaffold.py --name MyPlugin --author "Your Name" --dir E:/SkyrimTools/Proj/MyPlugin
python scripts/scaffold.py --help            # 查看全部选项
```

常用参数：

- `--name`：插件/工程名（同时用作 DLL 名、CMake project 名、日志文件名）。
- `--author`：SKSEPlugin_Version 的作者名。
- `--description`：README 与 project 描述。
- `--version`：形如 `1.0.0`。
- `--runtimes {all|se|ae|vr|se-ae|se-vr|ae-vr}`：默认 `all`（SE+AE+VR 单 DLL）。
- `--features config,hotkey,present_hook,vtable_hook,event_sink`：按需加入功能模块。
- `--commonlib {ng|vr}`：默认 `ng`（CommonLibSSE-NG）；`vr` 选 CommonLibVR（ng 分支）。
- `--dir`：输出目录（默认当前目录下的 `--name`）。
- `--git-init`：生成后 `git init` 并添加 CommonLibSSE submodule（需网络）。

生成后：

```powershell
cd <新项目>
git submodule update --init --recursive   # 拉取 extern/CommonLibSSE（及其 extern/openvr）
cmake --preset "msvc release"             # 配置（需 VCPKG_ROOT，首次会装依赖）
cmake --build --preset "msvc release"     # 产物 "build/msvc release/src/Release/<Name>.dll"
```

> CommonLibSSE 官方仍通过 git submodule 消费（未进官方 vcpkg 源），所以模板默认
> `.gitmodules` 指向 submodule，与两个源项目一致；不改为 vcpkg 引入。

## 结构速览（详细见 references/structure.md）

```text
<Project>/
├── .gitignore / .gitmodules
├── CMakeLists.txt          # project() + ENABLE_SKYRIM_SE/AE/VR 选项 + add_subdirectory(src) + packaging
├── CMakePresets.json       # msvc release：VS2022 + vcpkg toolchain + x64-windows-static-md + 14.44 工具集
├── vcpkg.json              # fmt/spdlog/directxmath/directxtk(+simpleini 按需)
├── cmake/                  # packaging.cmake / Plugin.h.in / version.rc.in
├── extern/CommonLibSSE/    # submodule（多运行时引擎库）
└── src/
    ├── CMakeLists.txt      # SHARED 目标、PCH、MSVC 旗标、CommonLibSSE add_subdirectory、链接、安装
    ├── pch.h               # CommonLibSSE + spdlog/fmt + Plugin.h + DLLEXPORT/logger/util
    ├── main.cpp            # SKSEPlugin_Query/_Version/_Load + 日志 + 消息回调
    └── <feature>.*         # 可选模块（config/input/esp_renderer/hooks/hit_events）
```

## 执行流程

1. 新建项目：运行 `scripts/scaffold.py`（或按用户指定手工生成），参数缺失时先问清
   `--name`、`--author`、`--runtimes`、`--features`。
2. 扩展既有插件：先读 `references/structure.md` 与 `references/patterns.md`，保持既有
   目录、目标与工具链一致；按需套用对应模式，不整仓重排。
3. 多运行时功能：阅读 `references/multi-runtime.md`——涉及运行时差异的地址/虚表一律走
   CommonLibSSE 的 `REL::Relocation` + 地址库（`RE::VTABLE_*[0]`），禁止硬编码单一运行时地址。
4. 编写/修改 C++ 与 CMake：遵循上列组件 `small-project-cpp-rules/SKILL.md`，并按任务读取其
   `references/cpp-style.md` 与 `references/cmake-style.md`（绿地默认值）。
5. 构建与验证：按 `references/build-and-verify.md` 执行最窄构建与清单核对。

## 按任务读取内置参考

- 目录/文件职责、如何增删模块：读取 [structure.md](references/structure.md)。
- SE/AE/VR 多运行时机制与地址库用法：读取 [multi-runtime.md](references/multi-runtime.md)。
- 可复用代码模式（入口/日志/消息/INI/热键/渲染/钩子/事件）：读取 [patterns.md](references/patterns.md)。
- 构建预设、工具链对齐、VR 前置、验证清单：读取 [build-and-verify.md](references/build-and-verify.md)。

不得只依据本页摘要动手；涉及上述领域必须读取对应内置参考，并遵守上述
`small-project-cpp-rules` 组件的工程规则。
