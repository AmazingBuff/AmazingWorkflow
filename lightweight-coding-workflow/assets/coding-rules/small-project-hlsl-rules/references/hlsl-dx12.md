# HLSL：DX12 与可选 Vulkan

先读 [共同规范](../SKILL.md) 及其引用的 cpp-style。本规范以 engine 的 DX12 HLSL 组织为基线，使用 DXC 生成 DXIL，需要 Vulkan 时从同一源生成 SPIR-V。

## 目标与资源

- 基线选择满足功能的最低 SM6 profile；样本 `compile.bat` 是 `cs_6_0`。阶段使用 `vs_6_x` / `ps_6_x` / `cs_6_x` 等，不因“DX12”就启用高版本特性。
- `ConstantBuffer<T>`、`Texture2D<T>`、`RWTexture2D<T>`、`SamplerState` 显式声明。SRV/UAV 的类型须与 host view 格式匹配。
- 常量数据先定义 `struct T`，再声明 `ConstantBuffer<T> b_name`，通过 `b_name.field` 访问；新增或实际修改的常量缓冲声明使用此形式，避免 `cbuffer { ... }` 声明块。Vulkan descriptor 与 push constant 两种情况均遵循这条规则，不批量改写无关旧代码。
- 使用 `register(bN/tN/uN/sN, spaceM)`，与 root signature、descriptor table 的寄存器范围和 stage visibility 一致。按更新频率或项目管线组织 space；样本按资源类别分 space 是可用布局，不是强制通则。
- wave、16-bit、bindless、mesh/ray 等能力按实际 SM、设备和目标后端支持选择，不从 DX12 基线自动推导可用。

## D3DCompile 与 SM5.1

如果 DX12 代码需要 DXBC 而不是 DXIL，可以继续使用 `D3DCompile`，但必须选择 `vs_5_1`、`ps_5_1`、`cs_5_1` 等 SM5.1 profile。SM5.1 支持 `ConstantBuffer<T>`，包括带 `space` 的寄存器声明；它属于 DX12 shader 路径，不是普通 DX11 SM5.0 shader 路径。`D3DCompile` 不能以 `cs_6_0` 生成 DXIL；DXIL 或 SPIR-V 仍使用 DXC。

最小调用约定如下：

```text
D3DCompile(source, size, name, macros, include, entry, "cs_5_1", flags, effect_flags, &blob, &errors)
```

同一份 `ConstantBuffer<T>` 源码在本机 `d3dcompiler_47.dll` 的结果为：`cs_5_0` 返回 `X3000: unrecognized identifier 'ConstantBuffer'`；`cs_5_1` 返回 `S_OK` 并生成 `DXBC`。使用 `register(b0, space3)` 的 `ps_5_1` 变体同样返回 `S_OK`。这证明的是编译器和目标 profile 的支持，不替代实际 D3D12 device/PSO、root signature 或资源绑定验证。

## 何时使用 Vulkan binding

仅 DX12 不必添加 `vk` 属性；同源输出 SPIR-V 且需要固定 descriptor layout 或默认映射冲突时，使用 `[[vk::binding(binding, set)]]`。项目已经统一用构建参数映射时沿用该机制，避免再引入一套规则。

`register` 描述 DirectX 绑定；`vk::binding` 描述 Vulkan 绑定，两者须各自匹配 host，编号不必相同。Vulkan 同一 set 的 binding 不按 b/t/u/s 分命名空间，因此 `b0, space0` 和 `t0, space0` 不能不加区分地映射到 `(0, 0)`。无显式映射时 DXC 默认把 register 数字映射为 binding、space 映射为 set；同一资源数组通常占一个 binding，descriptor count 由数组长度决定。

如需后端隔离，用 `__spirv__` 包围属性即可，不为几处声明预建复杂宏框架。下例是一个可双目标编译的完整 compute 案例，Vulkan set 0 的三个 binding 无冲突：

```hlsl
//
// Created by AmazingBuff on 2026/09/22.
//

struct FilterInfo
{
    float4 tint;
};

#ifdef __spirv__
[[vk::binding(0, 0)]]
#endif
ConstantBuffer<FilterInfo> b_filter : register(b0, space0);

#ifdef __spirv__
[[vk::binding(1, 0)]]
#endif
Texture2D<float4> t_source : register(t0, space0);

#ifdef __spirv__
[[vk::binding(2, 0)]]
#endif
RWTexture2D<float4> u_target : register(u0, space0);

[numthreads(8, 8, 1)]
void filter_image(uint3 thread_id : SV_DispatchThreadID)
{
    uint width, height;
    u_target.GetDimensions(width, height);
    if (thread_id.x >= width || thread_id.y >= height)
        return;

    u_target[thread_id.xy] = t_source.Load(int3(thread_id.xy, 0)) * b_filter.tint;
}
```

案例契约：host 绑定同尺寸源/目标，使用不同资源，初始化 tint，并以 `ceil(width/8), ceil(height/8), 1` dispatch。这里只有一次与真实 dispatch 对应的检查。

## Push constant 与布局

沿用 `box.hlsl` / `blur.hlsl` 的小参数块思路时，可把变量声明为：

```hlsl
#ifdef __spirv__
[[vk::push_constant]]
#endif
ConstantBuffer<FilterInfo> b_filter : register(b0, space0);
```

这是替代上述 b_filter 声明的方案，不能重复声明。在 Vulkan 中它使用 push constant range，不再是普通 descriptor，不同时加 `vk::binding`；在 DX12 中仍由 root signature 映射到对应常量数据，使用 CBV 或与布局匹配的 root constants。HLSL 的变量名不会自动建立 root constants。

每个 Vulkan 入口最多静态使用一个 push constant block，其尺寸/offset/stage range 由 host 与设备限制决定。不要把大型 per-object 数组塞进 push constant。

DXIL 与 SPIR-V 的缓冲布局不可仅凭同一份结构体假定相同；按 CPU 上传布局选择编译参数和反射结果。`-fvk-use-dx-layout` 是有条件的布局选项，需要目标 Vulkan 支持相应布局能力，不能无条件追加。阶段间 Vulkan location 也须匹配；必要时显式 `vk::location`。Y 翻转、viewport、front-face 等坐标策略在项目中统一处理，避免 shader 与 host 重复翻转。

上述属性、映射和布局选项以 [DXC SPIR-V mapping manual](https://github.com/microsoft/DirectXShaderCompiler/blob/main/docs/SPIR-V.rst) 为依据；编译器版本与选项必须随构建记录固定。

## 编译与最小检查

保存完整案例为 `filter_image.hlsl`，示例 Vulkan 目标为 1.1（项目另有要求时替换）：

```text
dxc -T cs_6_0 -E filter_image -I . -Fo filter_image.dxil filter_image.hlsl
dxc -spirv -fspv-target-env=vulkan1.1 -T cs_6_0 -E filter_image -I . -Fo filter_image.spv filter_image.hlsl
```

复用这个案例检查所承诺的目标，不遍历全部 profile。资源布局发生改动时检查对应反射与 host 映射；涉及图像结果时用一个代表尺寸/输出检查代替大量编译组合。仅 DX12 的任务不运行 Vulkan 检查。

文档验证记录（2026/09/22）：上述完整 compute 案例使用 engine 随附的 `3rd/dxc/bin/x64/dxc.exe`，以这里列出的 profile/target 参数分别编译 DXIL、SPIR-V，退出码均为 0。未执行 GPU 渲染或验证 host pipeline。

补充验证记录（2026/09/22）：使用系统 `d3dcompiler_47.dll` 调用 `D3DCompile`，`ConstantBuffer<T>` 的 `cs_5_1` 与带 `space` 的 `ps_5_1` 均成功生成 DXBC；`cs_5_0` 失败。未执行 GPU 渲染或验证 host pipeline。
