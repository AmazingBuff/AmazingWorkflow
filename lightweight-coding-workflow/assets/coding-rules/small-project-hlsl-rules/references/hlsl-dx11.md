# HLSL：DX11

先读 [共同规范](../SKILL.md) 及其引用的 cpp-style。保留 engine 样本的 pass、IO、显式资源与入口组织；本文件规定其 DX11 兼容形式，不直接沿用 DX12 绑定语法。

## 编译基线

默认 DX11 feature level 11_0 与 SM5.0，阶段 profile 为 `vs_5_0`、`ps_5_0`、`cs_5_0` 等。若支持更低 feature level，按真实设备能力选择更低 profile 与算法，不能把所有 DX11 设备视为支持 SM5。使用 FXC 或 D3DCompile 生成 DXBC；DXC 的 DXIL/SPIR-V 产物不作为常规 DX11 shader 字节码。

依据：[Microsoft compiler targets](https://learn.microsoft.com/en-us/windows/win32/direct3dhlsl/specifying-compiler-targets)、[DXC FAQ](https://github.com/microsoft/DirectXShaderCompiler/wiki/FAQ)。

## ConstantBuffer<T> 优先与 SM5 兼容例外

项目风格优先使用 `struct T` 加 `ConstantBuffer<T>`，避免 `cbuffer` 声明块。但不能将此偏好写成传统 DX11 SM5.0 编译器已经支持的能力：本机 `d3dcompiler_47.dll` 在 `cs_5_0` 下编译 `ConstantBuffer<FilterInfo>` 返回 `X3000: unrecognized identifier 'ConstantBuffer'`。将 profile 改成 `cs_5_1` 后可以编译成功，但产物是 SM5.1/DX12 shader，不是普通 DX11 shader。Microsoft 的 [FXC/DXC 迁移说明](https://github.com/microsoft/DirectXShaderCompiler/wiki/Porting-shaders-from-FXC-to-DXC) 将该模板构造的引入关联到 SM5.1。

因此，下表及示例中的 `cbuffer` 仅用于维持已选定的 DX11 SM5.0 兼容性，不是推荐的通用编码风格。若目标实际是 DX12，应切换到 DX12 规范并使用 `ConstantBuffer<T>` + `D3DCompile(..., "*_5_1", ...)` 或 DXC；不得把 SM5.1 编译成功声称为 DX11 兼容。若用户完全禁止 `cbuffer`，而目标仍是传统 DX11 SM5.0，应明确报告编译基线冲突，不静默改为 SM5.1/DX12，也不自行引入转换器。

## 从 DX12 写法转换（传统 SM5.0 兼容路径）

| DX12 / Vulkan 写法 | DX11 SM5.0 规则 |
|---|---|
| `ConstantBuffer<PassInfo> b_pass` | 仅编译器不支持时使用兼容例外 `cbuffer PassBuffer { PassInfo b_pass; };`，保留 `b_pass.view` 等访问形态 |
| `register(t0, space1)` | `register(tN)`；由 host 明确分配 slot，不能只删除 space 导致重名冲突 |
| `vk::binding` / `vk::push_constant` | DX11 翻译单元中移除或由条件编译排除；小参数块使用常量缓冲，传统 SM5.0 声明适用上述兼容例外 |
| root signature / descriptor table | 对应 stage 的 `*SetConstantBuffers` / `*SetShaderResources` / `*SetSamplers` 等 host 绑定 |
| wave、SM6 原生 16-bit、descriptor heap 索引 | 使用已确认的 SM5 算法或独立变体，不能只换 profile |

不要把资源模板一概删除：`Texture2D<float4>`、`RWTexture2D<float4>`、`StructuredBuffer<T>` 等 SM5 支持的类型仍可使用。

## 绑定与数据

- 使用 `register(bN)`、`register(tN)`、`register(uN)`、`register(sN)`，没有 register space。b/t/u/s 是不同 slot 类别；绑定还取决于 shader stage。
- 固定数组及动态索引必须满足目标 profile/资源类型限制；不要引入 DX12 的无界资源数组或 bindless 假设。
- cbuffer 内容显式组织并遵守 packing；CPU constant buffer 的 ByteWidth 为 16 字节倍数，字段偏移仍按实际 packing 匹配，而非每个字段补到 16 字节。
- texture/sampler 分开声明；UAV 使用只针对支持的阶段和格式。pixel UAV 由 OM 路径管理，compute UAV 由 CS 路径管理，不套用 DX12 的任意阶段绑定习惯。
- host 管理资源读写冲突，避免同一子资源同时作为 SRV 和写入目标；shader 不负责“修复”host 绑定。

## 最小 compute 案例（SM5.0 兼容例外）

与 DX12 案例保持同一算法与 host 尺寸/dispatch 契约，只改变常量与资源声明：

```hlsl
//
// Created by AmazingBuff on 2026/09/22.
//

struct FilterInfo
{
    float4 tint;
};

cbuffer FilterBuffer : register(b0)
{
    FilterInfo b_filter;
};

Texture2D<float4> t_source : register(t0);
RWTexture2D<float4> u_target : register(u0);

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

保存为 `filter_image_dx11.hlsl`：

```text
fxc /T cs_5_0 /E filter_image /I . /Fo filter_image.dxbc filter_image_dx11.hlsl
```

只检查本次修改的代表入口；需要图像验证时选择一个能观察行为的案例，不扩展全阶段矩阵。缺少 FXC/D3DCompile 时如实记录未编译，不用 DXC 的 SM6 成功代替 DX11 兼容证据。

文档验证记录（2026/09/22）：本机未发现 FXC 命令，使用 `d3dcompiler_47.dll` 的 D3DCompile，以 `filter_image` / `cs_5_0` 编译上述案例，HRESULT 为 `S_OK`，产物容器头为 `DXBC`。未执行 GPU 渲染或验证 host pipeline。
