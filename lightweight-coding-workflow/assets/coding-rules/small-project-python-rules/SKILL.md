---
name: small-project-python-rules
description: Apply proportional Python project structure, typing, dependency, testing, visualization, and Python-to-C++ migration rules.
---

# Small Project Python Rules

> 组合适配版：改编自 small-project-workflow-spec 的同名规范（基线 `5fb6ec0`），作为 lightweight-coding-workflow 实现阶段的组件文档使用；仅调整编排词汇，代码规则未变。改动清单见 [../README.md](../README.md)。

本规范是 lightweight 编排框架内置且自包含的 Python 工程规范。不要读取、触发或依赖环境中的其他 Python 规范 skill；与随本规范一同提供的 `small-project-code-contract` 组合适配版同时使用。既有项目先服从 `pyproject.toml`、锁文件、格式化与检查配置、CI 和相邻第一方代码；只在触及范围内应用新默认值。

## 项目结构

绿地小项目默认从以下最小结构开始，并按真实职责渐进增加模块：

```text
pyproject.toml
src/<package>/
tests/
```

需要时再增加 `cli/`、`visualization/`、`adapters/`、`scripts/`、`examples/` 或 `docs/`。一次性工具可保持单文件；出现第二个稳定职责后再拆包。I/O、UI、文件、网络等副作用放在边界层，计算核心尽量保持纯函数。

## 代码规则

- 遵循 PEP 8：模块、函数、变量用 `snake_case`，类用 `PascalCase`，常量用 `UPPER_SNAKE_CASE`，4 空格缩进。
- 导入按标准库、第三方、本项目分组；优先绝对导入；禁用 wildcard import 和 `sys.path` hack。
- 公开函数和非平凡函数提供类型标注；类型标注是静态契约，不得在可信内部用运行时类型装饰器重复校验。
- 轻量数据和值对象优先 `dataclass` 或明确类型；只有真实运行时替换需求才使用窄 `Protocol`、ABC 或 callable。
- 资源使用 context manager，路径使用 `pathlib`；同层统一异常模型，只在边界补充上下文或转换异常。
- 禁止可变默认参数、裸 `except`、静默吞错、无必要的全局可变状态和导入期副作用。
- 函数拆分与输入校验严格遵循全局 code contract。

## 技术与依赖建议

标准库足够时不增加依赖。按需求候选：

- 数值和数组：NumPy；科学计算：SciPy；
- 表格：pandas 或 Polars 二选一；
- 静态可视化：Matplotlib，现有生态需要时可搭配 Seaborn；交互可视化：Plotly；
- 图像：Pillow；计算机视觉：OpenCV；桌面 UI：PySide6；
- 复杂外部 schema 边界：Pydantic，禁止用它给内部可信对象重复验证；
- 工程工具：Ruff 与 pytest；类型风险明显时选择 mypy 或 pyright。

不得无理由同时引入职责重叠的库。所有依赖必须在技术方案中说明收益、替代、许可、版本与平台代价。

## Python 转 C++

迁移是语义和契约等价，不是逐行翻译。先 profile 证明性能、部署、SDK、内存或实时性约束；隔离计算内核与 I/O/可视化；冻结输入输出 schema、dtype、shape、单位、布局、随机性、错误语义和数值容差；用同一 golden data 做 Python/C++ 差分测试。通常保留 Python 可视化，按需要选择 CLI、文件接口、pybind11 或 nanobind 连接 C++ 核心。过渡期只能有一个业务规则权威实现。

## 最小检查

运行仓库既有命令；绿地默认至少执行 Ruff、pytest，以及已启用的类型检查。无测试数据时仍需覆盖导入、启动和一条代表路径。
