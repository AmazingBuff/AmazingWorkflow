---
name: skse-plugin-template
description: Plan file layout, configure CMake and adapt selected reusable code for a C++23 SKSE plugin, using Highlight-Lootable-Corpses as an organizational reference. Generate a minimal plugin by default; select reusable modules from templates/features only when needed.
---

# SKSE 插件结构与复用

本 skill 主要指导三件事：**如何编排文件、如何配置 CMake、如何按需调整可复用代码**。
Highlight-Lootable-Corpses 提供组织方式和具体实现参考，不是必须复制的模块清单。
先从插件的实际功能出发，再选择需要的目录、依赖和实现。

## 工作顺序

1. 阅读现有项目和用户需求，确定本次功能需要哪些运行时能力。维护已有项目时保留其有效结构。
2. 给出本次文件布局及职责、CMake 增量、拟复用代码的来源和裁剪范围；小任务简要说明即可。
3. 新项目先生成最小可加载插件，再为实际功能增加文件。不要预建空模块，也不要因参考项目存在某模块就引入它。
4. 选取参考实现时检查依赖、对象所有权、调用线程、生命周期和运行时适配；删掉原业务耦合后接入。
5. 只验证本次实际生成或修改的内容。编译、单元测试和游戏内验证分别报告。

与 lightweight-coding-workflow 同时使用时，以 lightweight 为主：由其 Planner 管理范围、授权、实现契约和验证，由同一实现 worker 执行生成或修改；本 skill 只补充 SKSE 文件组织、CMake 和代码复用规则。既有用户授权继续有效，不建立第二套规划/审批流程或额外 writer，也不绕过 lightweight 的职责边界。

单独使用本 skill 时，用户已要求实现便直接完成已明确的工作，不为本流程额外要求新任务或重复授权。

## 默认模板边界

```text
CMakeLists.txt          根目录统一定义插件 target、依赖和编译设置
CMakePresets.json       工具链、架构、vcpkg 与构建目录
vcpkg.json             当前依赖清单
.gitmodules            CommonLib 来源配置；不等于已获取子模块
cmake/
  plugin.h.in          CMake 配置项目元数据和命名空间
  version.rc.in        Windows DLL 版本资源
  packaging.cmake      保留构建组织示例，发布时另行定义实际安装内容
src/
  main.cpp             日志、SKSE 初始化和导出
  pch.h                核心头文件和项目公共别名
```

默认生成的项目 **不包含** config、input、ui、render、base 工具集、事件/虚表 hook、ShaderManager、
SKSE-MCP、着色器或任何游戏业务代码，也不注册没有用途的消息/事件处理器。
模板中的 CommonLib 传递依赖不代表插件已经实现对应功能。

```powershell
python scripts/scaffold.py --name MyPlugin --namespace MyTeam --author "Your Name" --dir C:/work/MyPlugin
```

输出目录必须为空；默认只生成文件。--git-init 仅初始化本地 Git；--add-submodules 获取
CommonLib 及所选 feature 的子模块。--display-name 只设置 README 标题，不会自动引入菜单。

## 按需 feature

可选模块位于 `templates/features/<name>/`。不传 `--features` 时仍生成上述最小模板。

```powershell
python scripts/scaffold.py --name MyPlugin --features input --dir C:/work/MyPlugin
python scripts/scaffold.py --name MyPlugin --features config,input,menu --dir C:/work/MyPlugin
python scripts/scaffold.py --name MyPlugin --features render,shaders --dir C:/work/MyPlugin
```

依赖自动补齐并去重，例如 input 自动包含 config；不会自动选择菜单或渲染。
`--features none` 显式选择最小模板；`all` 适合验证全集，不是默认建议。
每个 feature 包含 feature.json 和要复制到项目根目录的 src/cmake 子树。
生成器同步接入文件、CMake、vcpkg、子模块、头文件和对应生命周期。
输出目录仍必须为空；对已有项目按 manifest 逐项迁移，不覆盖现有代码。
详见 [features.md](references/features.md)。

## 三类参考

- [file-layout.md](references/file-layout.md)：按职责增加文件、控制入口文件和公共头的边界。
- [build-and-verify.md](references/build-and-verify.md)：根 CMake 的组织、按需依赖/资源接入及验证。
- [reuse-guide.md](references/reuse-guide.md)：选择参考代码、拆除业务耦合并保持接口与调用链一致。
- [reference-project.md](references/reference-project.md)：参考工程的阅读入口及可学习的模式。
- [multi-runtime.md](references/multi-runtime.md)：有引擎事件、hook、渲染或跨运行时需求时再读取。

“保持一致”指采用清晰的责任划分、构建组织和可追踪的适配方式。它不要求文件数量、
模块集合、依赖列表、业务行为或代码哈希与参考工程相同。不要要求先修改参考工程才能
修复目标项目，也不要用逐文件相等检查限制必要裁剪。

## 校验 skill

```powershell
python scripts/test_scaffold.py
python -X utf8 <skill-creator-root>/scripts/quick_validate.py <skill-directory>
```

默认运行两个代表案例：最小插件边界，以及 config + shaders 的依赖和生成接入。只想验证一个受影响行为时，可直接指定 unittest 测试名；维护生成器依赖解析或发布前确有全量回归需要时，显式运行 `python scripts/test_scaffold.py --full`，不要把全量矩阵作为日常默认。

普通插件任务只选本次实际受影响的 1–2 个案例，不因使用模板而执行生成器全量测试。与 lightweight 组合时服从实现契约的 Verification 和 Codex 测试预算。编译、游戏内验证与未验证部分分别报告。
