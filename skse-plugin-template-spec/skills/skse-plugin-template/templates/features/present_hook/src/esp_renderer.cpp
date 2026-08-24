//
// Created by AmazingBuff on {{DATE}}.
//

#include "esp_renderer.h"

#include <d3d11.h>
#include <dxgi.h>
#include <CommonStates.h>
#include <DirectXMath.h>
#include <Effects.h>
#include <PrimitiveBatch.h>
#include <VertexTypes.h>
{{RENDERER_EXTRA_INCLUDES}}

namespace
{

using Present_t = HRESULT(STDMETHODCALLTYPE*)(IDXGISwapChain*, UINT, UINT);
Present_t g_original_present = nullptr;
void** g_hooked_slot = nullptr;

std::unique_ptr<DirectX::CommonStates> g_states;
std::unique_ptr<DirectX::BasicEffect> g_effect;
std::unique_ptr<DirectX::PrimitiveBatch<DirectX::VertexPositionColor>> g_batch;

// 后台缓冲 RTV（懒创建，渲染线程独占）
ID3D11RenderTargetView* g_back_buffer_rtv = nullptr;
ID3D11Texture2D* g_back_buffer = nullptr;
std::uint32_t g_back_w = 0;
std::uint32_t g_back_h = 0;

bool ensure_back_buffer(IDXGISwapChain* a_swapChain, ID3D11Device* a_device)
{
    ID3D11Texture2D* buffer = nullptr;
    HRESULT const hr = a_swapChain->GetBuffer(0, __uuidof(ID3D11Texture2D), reinterpret_cast<void**>(&buffer));
    if (FAILED(hr) || !buffer)
    {
        return false;
    }

    if (buffer == g_back_buffer)
    {
        buffer->Release();
        return true;
    }

    if (g_back_buffer_rtv)
    {
        g_back_buffer_rtv->Release();
        g_back_buffer_rtv = nullptr;
    }
    if (g_back_buffer)
    {
        g_back_buffer->Release();
        g_back_buffer = nullptr;
    }

    g_back_buffer = buffer;
    D3D11_TEXTURE2D_DESC desc{};
    buffer->GetDesc(&desc);
    g_back_w = desc.Width;
    g_back_h = desc.Height;

    HRESULT const rtv_hr = a_device->CreateRenderTargetView(buffer, nullptr, &g_back_buffer_rtv);
    if (FAILED(rtv_hr) || !g_back_buffer_rtv)
    {
        logger::error("Failed to create backbuffer RTV: {:X}", static_cast<unsigned int>(rtv_hr));
        return false;
    }
    return true;
}

void ensure_draw_resources(ID3D11Device* a_device, ID3D11DeviceContext* a_context)
{
    if (!g_states)
    {
        g_states = std::make_unique<DirectX::CommonStates>(a_device);
    }
    if (!g_effect)
    {
        g_effect = std::make_unique<DirectX::BasicEffect>(a_device);
        g_effect->SetVertexColorEnabled(true);
    }
    if (!g_batch)
    {
        g_batch = std::make_unique<DirectX::PrimitiveBatch<DirectX::VertexPositionColor>>(a_context);
    }
}

void on_present_inner(IDXGISwapChain* a_swapChain)
{
    {{ON_PRESENT_BODY}}

    auto* renderer = RE::BSGraphics::Renderer::GetSingleton();
    if (!renderer)
    {
        return;
    }

    auto& rt = renderer->GetRuntimeData();
    auto* device = reinterpret_cast<ID3D11Device*>(rt.forwarder);
    auto* context = reinterpret_cast<ID3D11DeviceContext*>(rt.context);
    if (!device || !context)
    {
        return;
    }

    if (!ensure_back_buffer(a_swapChain, device))
    {
        return;
    }

    ensure_draw_resources(device, context);
    if (!g_states || !g_effect || !g_batch)
    {
        return;
    }

    float const w = static_cast<float>(g_back_w);
    float const h = static_cast<float>(g_back_h);
    if (w <= 0.0f || h <= 0.0f)
    {
        return;
    }

    // ---- 保存游戏渲染状态，设置本插件的绘制状态 ----
    ID3D11RenderTargetView* prev_rtv = nullptr;
    ID3D11DepthStencilView* prev_dsv = nullptr;
    context->OMGetRenderTargets(1, &prev_rtv, &prev_dsv);
    context->OMSetRenderTargets(1, &g_back_buffer_rtv, nullptr);

    ID3D11BlendState* prev_blend = nullptr;
    float blend_factor[4]{};
    UINT sample_mask = 0;
    context->OMGetBlendState(&prev_blend, blend_factor, &sample_mask);

    ID3D11DepthStencilState* prev_depth = nullptr;
    UINT prev_stencil = 0;
    context->OMGetDepthStencilState(&prev_depth, &prev_stencil);

    ID3D11RasterizerState* prev_rs = nullptr;
    context->RSGetState(&prev_rs);

    context->OMSetBlendState(g_states->AlphaBlend(), nullptr, 0xFFFFFFFF);
    context->OMSetDepthStencilState(g_states->DepthNone(), 0);
    context->RSSetState(g_states->CullNone());

    g_effect->SetWorld(DirectX::XMMatrixIdentity());
    g_effect->SetView(DirectX::XMMatrixIdentity());
    g_effect->SetProjection(DirectX::XMMatrixOrthographicOffCenterLH(0.0f, w, h, 0.0f, 0.0f, 1.0f));
    g_effect->Apply(context);

    g_batch->Begin();
    // ... 在此实现具体绘制（PrimitiveBatch 画点/线/矩形）...
    g_batch->End();

    // ---- 恢复游戏渲染状态 ----
    context->OMSetRenderTargets(1, &prev_rtv, prev_dsv);
    context->OMSetBlendState(prev_blend, blend_factor, sample_mask);
    context->OMSetDepthStencilState(prev_depth, prev_stencil);
    context->RSSetState(prev_rs);

    if (prev_rtv) prev_rtv->Release();
    if (prev_dsv) prev_dsv->Release();
    if (prev_blend) prev_blend->Release();
    if (prev_depth) prev_depth->Release();
    if (prev_rs) prev_rs->Release();
}

HRESULT STDMETHODCALLTYPE present_thunk(IDXGISwapChain* a_swapChain, UINT a_syncInterval, UINT a_flags)
{
    on_present_inner(a_swapChain);
    return g_original_present(a_swapChain, a_syncInterval, a_flags);
}
}

namespace ESPRenderer
{

void install()
{
    if (g_hooked_slot)
    {
        return;  // 幂等
    }

    auto* renderer = RE::BSGraphics::Renderer::GetSingleton();
    if (!renderer)
    {
        return;
    }

    auto& rt = renderer->GetRuntimeData();
    if (!rt.renderWindows || !rt.renderWindows[0].swapChain)
    {
        logger::warn("SwapChain not available yet, will retry on next game message");
        return;
    }

    // IDXGISwapChain::Present 是虚函数表第 8 槽位（与运行时版本无关）
    auto* swapChain = reinterpret_cast<IDXGISwapChain*>(rt.renderWindows[0].swapChain);
    void** vtable = *reinterpret_cast<void***>(swapChain);

    g_hooked_slot = &vtable[8];
    g_original_present = reinterpret_cast<Present_t>(*g_hooked_slot);

    DWORD old_protect = 0;
    if (!VirtualProtect(g_hooked_slot, sizeof(void*), PAGE_READWRITE, &old_protect))
    {
        logger::error("VirtualProtect failed, cannot install Present hook");
        g_hooked_slot = nullptr;
        g_original_present = nullptr;
        return;
    }
    *g_hooked_slot = reinterpret_cast<void*>(&present_thunk);
    VirtualProtect(g_hooked_slot, sizeof(void*), old_protect, &old_protect);

    logger::info("Installed IDXGISwapChain::Present hook (swapchain={})", fmt::ptr(swapChain));
}

void on_present(IDXGISwapChain* a_swapChain)
{
    on_present_inner(a_swapChain);
}
}
