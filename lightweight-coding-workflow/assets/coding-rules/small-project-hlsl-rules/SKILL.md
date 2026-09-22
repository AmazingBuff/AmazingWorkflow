---
name: small-project-hlsl-rules
description: Apply HLSL coding rules derived from the engine shaders and the bundled C++ style, selecting DX12 with optional Vulkan SPIR-V bindings or DX11 SM5 compatibility.
---

# HLSL 编码规范

适用于新增或实际修改的 `.hlsl` / `.hlsli`。先读本文件和
[cpp-style.md](../small-project-cpp-rules/references/cpp-style.md)，再按目标读取：

| 目标 | 必读规范 | 编译产物 |
|---|---|---|
| DX12，或 DX12/Vulkan 共用 HLSL | [DX12 规范](references/hlsl-dx12.md) | DXC → DXIL；需要 Vulkan 时 DXC → SPIR-V |
| DX11 | [DX11 规范](references/hlsl-dx11.md) | FXC / D3DCompile → DXBC，默认 SM5.0 |

跨两个目标时读取两份；不把 DX12 源码直接标记为 DX11 兼容。Planner 将本文件、cpp-style 和选定目标规范的绝对路径列入 Applicable coding rules，并记录入口、profile、编译器、目标 API 和绑定/布局约定。规范自包含，使用时不要求访问原始 engine 仓库。

## 来源与适用边界

2026/09/22 阅读 `D:/code/github/engine/res/shader` 的 `common.hlsl`、`box/box.hlsl`、`quad/quad.hlsl`、`triangle/triangle.hlsl`、`graph_triangle/graph_triangle.hlsl`、`mipmap/mip.hlsl`、`post-processing/blur.hlsl`、`aa/smaa.hlsl` 和 `compile.bat`。

提取其按 pass 分文件、共享数据结构、显式寄存器、独立 texture/sampler、简单入口函数和 compute kernel 的组织方式。DX12 版以这些样本为依据；DX11 版是对相同组织与算法的兼容改写规则，并非宣称样本本来就是 DX11。零散旧命名、未使用变量、未完成算法不构成规范；如 `smaa.hlsl` 的输出资源名称不一致，不应照搬。

## 继承 cpp-style 的基础规范

继承小写下划线文件名、4 空格缩进、Allman 大括号、最小作用域、精确类型、必要时才拆函数、最小改动面和仅为复杂逻辑写必要英文注释。新文件沿用 cpp-style 的作者/实际日期头。现有项目稳定风格与已发布接口优先。

| 对象 | HLSL 写法 |
|---|---|
| 类型 | `PascalCase`：`VertexAttribute`、`VertexOutput`、`PassInfo` |
| 函数、参数、局部变量、数据字段 | `snake_case`：`mean_blur`、`thread_id`、`mip_level` |
| 全局编译期常量 | `Upper_Snake_Case`：`Thread_Group_Size_X` |
| 宏 | `ALL_CAPS`；仅用于真正的编译期变体 |
| 常量缓冲、SRV、UAV、sampler 实例 | `b_`、`t_`、`u_`、`s_`：`b_pass`、`t_source`、`u_target`、`s_linear` |
| 其他普通全局变量 | 沿用 cpp-style 的 `g_`；不要用其代替资源类别前缀 |
| 入口与语义 | 保留管线约定，如 `vs`、`ps`、`mipmap`、`SV_Position`、`SV_Target0` |

HLSL 的数据结构字段是 shader IO / GPU 数据契约，使用样本的 `position`、`texcoord`，不套 C++ 类的 `m_`。`s_` 用于 sampler 是显式语言例外。局部常量采用 `float const threshold`，全局常量可用 `static float const Threshold`。

不把 C++ 的类层次、RAII、指针、`std` 类型、`enum class`、designated initializer、`noexcept`、named cast 或强制命名空间搬进 HLSL。数值类型使用 `float`、`uint`、`int` 及其向量/矩阵；转换用 HLSL 构造式，如 `float2(thread_id.xy)`。GPU 数据结构只放字段，不用成员默认初始化，返回前填好真正被消费的输出。

## 文件与接口

- 按 pass/功能组织目录；入口文件 `.hlsl`，新共享声明优先 `.hlsli`，已有 `common.hlsl` 可保留。
- 顺序为共享 include、数据类型/常量、资源声明、必要辅助函数、入口；同一 pass 的 `vs`/`ps` 可共文件，以 `-E` 或 `/E` 分别编译。
- include 使用配置好的 shader include 根，禁止 `../`。共享文件沿用已有保护方式；跨 FXC/DXC 新文件可用宏保护，不强制 C++ 的 `#pragma once`。
- IO 显式标注 semantic，阶段间字段类型、插值修饰和索引保持一致；顶点裁剪位置使用 `SV_Position`，颜色使用 `SV_TargetN`。整数插值数据需要 `nointerpolation`。
- 保留矩阵方向与 `mul` 参数顺序，明确世界/视图/裁剪空间。`row_major` / `column_major` 决定存储方式，不会替你选择数学上的左乘或右乘；不得为后端切换随意转置。

## 数据布局与执行逻辑

- 常量缓冲统一优先采用独立数据结构加 `ConstantBuffer<T>` 实例，避免直接使用 `cbuffer` 声明块；DX12/Vulkan 新代码必须采用此形式。仅 DX11 SM5 编译器不支持该语法时，按 DX11 规范保留必要的兼容例外，不将 `cbuffer` 作为通用风格推荐。若任务明确禁止任何 `cbuffer`，先说明与既定 DX11 编译基线的冲突，不擅自降级写法或改换目标。
- CPU/GPU 共享字段按实际布局与反射结果匹配偏移、矩阵约定、数组 stride 和总大小。不得套用 C++ 配置结构体的字段排序规则，也不得假设 C++ `sizeof` 等于 HLSL 大小。
- 常量缓冲按 HLSL packing 规则处理，`ConstantBuffer<T>` 不会免除布局约束；不是每个字段都独占 16 字节，也不能把数组当 C++ 紧密数组。对跨 CPU/GPU 的标志优先 `uint`，避免 C++ `bool` 大小差异。[Microsoft packing rules](https://learn.microsoft.com/en-us/windows/win32/direct3dhlsl/dx-graphics-hlsl-packing-rules)
- 采样用 `Texture*.Sample`（隐式导数可用的阶段）、`SampleLevel`（显式 LOD）或 `Load`（整数 texel）；compute 基线使用 `SampleLevel`/`Load`，不依赖未确认的高版本导数能力。像素步长用 `1.0 / width`，避免整数除法。
- 信任 CPU 已保证的尺寸、资源与参数条件，不在每个 helper 重复校验或增加 `Validate*`。滤波的 `clamp` 属于算法的边缘策略，应保留。
- dispatch 若向上取整且覆盖非整组尺寸，在 kernel 入口做一次真实的越界处理；若 CPU 已保证恰好覆盖则无需重复检查。涉及组同步时，不能让部分线程提前返回而其他线程进入 barrier；应让所有组线程参与同步，仅屏蔽无效访问。
- shader 内的组同步不能替代 CPU 侧 pass 间资源同步；只有确实共享数据时才使用 `groupshared` 与 barrier，不预设额外同步或分支。

## 最小验证

遵循 Codex adapter 的总预算：每次变更选 1–2 个代表案例，不按入口、文件、后端组合生成测试矩阵。纯规范修改可做文档/格式检查；若有可执行示例，优先复用同一案例检查目标编译。双后端承诺应对同一案例生成 DXIL 和 SPIR-V；这属于一个案例的必要目标检查。涉及 DX11 时选择一个 SM5 案例。仅编译成功不能证明绑定、渲染结果或 CPU 数据布局正确；明确记录未验证的部分。
