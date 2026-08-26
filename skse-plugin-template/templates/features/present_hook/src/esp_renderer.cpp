//
// Created by AmazingBuff on {{DATE}}.
//

#include "esp_renderer.h"

{{RENDERER_EXTRA_INCLUDES}}

#include <CommonStates.h>
#include <DirectXMath.h>
#include <Effects.h>
#include <PrimitiveBatch.h>
#include <VertexTypes.h>
#include <wrl/client.h>

#include <exception>
#include <memory>
#include <string_view>
#include <utility>

namespace {{PROJECT_NAMESPACE}}
{
namespace esp_renderer
{
namespace
{

using Microsoft::WRL::ComPtr;
using Present = HRESULT(STDMETHODCALLTYPE*)(IDXGISwapChain*, UINT, UINT);

Present g_original_present = nullptr;
void** g_hooked_slot = nullptr;

struct DrawResources
{
    ComPtr<ID3D11Device> device;
    ComPtr<ID3D11DeviceContext> deferred_context;
    std::unique_ptr<DirectX::CommonStates> states;
    std::unique_ptr<DirectX::BasicEffect> effect;
    std::unique_ptr<DirectX::PrimitiveBatch<DirectX::VertexPositionColor>> batch;

    void reset() noexcept
    {
        batch.reset();
        effect.reset();
        states.reset();
        deferred_context.Reset();
        device.Reset();
    }
};

DrawResources g_draw_resources;

bool ensure_draw_resources(ID3D11Device* device)
{
    if (
        g_draw_resources.device.Get() == device &&
        g_draw_resources.deferred_context &&
        g_draw_resources.states &&
        g_draw_resources.effect &&
        g_draw_resources.batch)
    {
        return true;
    }

    g_draw_resources.reset();

    ComPtr<ID3D11DeviceContext> deferred_context;
    HRESULT const context_result = device->CreateDeferredContext(
        0,
        deferred_context.ReleaseAndGetAddressOf()
    );
    if (FAILED(context_result))
    {
        SKSE::log::error(
            "Failed to create deferred D3D11 context: 0x{:08X}",
            static_cast<unsigned int>(context_result)
        );
        return false;
    }

    try
    {
        g_draw_resources.states = std::make_unique<DirectX::CommonStates>(device);
        g_draw_resources.effect = std::make_unique<DirectX::BasicEffect>(device);
        g_draw_resources.effect->SetVertexColorEnabled(true);
        g_draw_resources.batch = std::make_unique<
            DirectX::PrimitiveBatch<DirectX::VertexPositionColor>
        >(deferred_context.Get());
    }
    catch (std::exception const& error)
    {
        SKSE::log::error("Failed to create D3D11 draw resources: {}", error.what());
        g_draw_resources.reset();
        return false;
    }

    g_draw_resources.device = device;
    g_draw_resources.deferred_context = std::move(deferred_context);
    return true;
}

void record_and_execute(IDXGISwapChain* swap_chain)
{
    ComPtr<ID3D11Device> device;
    HRESULT const device_result = swap_chain->GetDevice(
        __uuidof(ID3D11Device),
        reinterpret_cast<void**>(device.ReleaseAndGetAddressOf())
    );
    if (FAILED(device_result) || !device)
    {
        return;
    }
    if (!ensure_draw_resources(device.Get()))
    {
        return;
    }

    ComPtr<ID3D11Texture2D> back_buffer;
    HRESULT const buffer_result = swap_chain->GetBuffer(
        0,
        __uuidof(ID3D11Texture2D),
        reinterpret_cast<void**>(back_buffer.ReleaseAndGetAddressOf())
    );
    if (FAILED(buffer_result) || !back_buffer)
    {
        return;
    }

    D3D11_TEXTURE2D_DESC back_buffer_description{};
    back_buffer->GetDesc(&back_buffer_description);
    if (back_buffer_description.Width == 0 || back_buffer_description.Height == 0)
    {
        return;
    }

    ComPtr<ID3D11RenderTargetView> render_target_view;
    HRESULT const view_result = device->CreateRenderTargetView(
        back_buffer.Get(),
        nullptr,
        render_target_view.ReleaseAndGetAddressOf()
    );
    if (FAILED(view_result) || !render_target_view)
    {
        SKSE::log::error(
            "Failed to create per-frame back-buffer view: 0x{:08X}",
            static_cast<unsigned int>(view_result)
        );
        return;
    }

    ID3D11DeviceContext* const deferred_context = g_draw_resources.deferred_context.Get();
    deferred_context->ClearState();
    ID3D11RenderTargetView* const render_targets[] = { render_target_view.Get() };
    deferred_context->OMSetRenderTargets(1, render_targets, nullptr);
    deferred_context->OMSetBlendState(g_draw_resources.states->AlphaBlend(), nullptr, 0xFFFFFFFF);
    deferred_context->OMSetDepthStencilState(g_draw_resources.states->DepthNone(), 0);
    deferred_context->RSSetState(g_draw_resources.states->CullNone());

    float const width = static_cast<float>(back_buffer_description.Width);
    float const height = static_cast<float>(back_buffer_description.Height);
    g_draw_resources.effect->SetWorld(DirectX::XMMatrixIdentity());
    g_draw_resources.effect->SetView(DirectX::XMMatrixIdentity());
    g_draw_resources.effect->SetProjection(
        DirectX::XMMatrixOrthographicOffCenterLH(0.0f, width, height, 0.0f, 0.0f, 1.0f)
    );
    g_draw_resources.effect->Apply(deferred_context);

    g_draw_resources.batch->Begin();
    // Record plugin overlay primitives here.
    g_draw_resources.batch->End();

    ComPtr<ID3D11CommandList> command_list;
    HRESULT const command_result = deferred_context->FinishCommandList(
        FALSE,
        command_list.ReleaseAndGetAddressOf()
    );
    deferred_context->ClearState();
    if (FAILED(command_result) || !command_list)
    {
        SKSE::log::error(
            "Failed to finish deferred D3D11 command list: 0x{:08X}",
            static_cast<unsigned int>(command_result)
        );
        return;
    }

    ComPtr<ID3D11DeviceContext> immediate_context;
    device->GetImmediateContext(immediate_context.ReleaseAndGetAddressOf());
    if (!immediate_context)
    {
        return;
    }

    // TRUE restores every immediate-context pipeline state after command execution.
    immediate_context->ExecuteCommandList(command_list.Get(), TRUE);
}

void on_present_inner(IDXGISwapChain* swap_chain)
{
    {{ON_PRESENT_BODY}}
    record_and_execute(swap_chain);
}

void report_present_failure(std::string_view reason) noexcept
{
    try
    {
        SKSE::log::error("Present overlay failed: {}", reason);
    }
    catch (...)
    {
        // Diagnostics are best-effort while containing exceptions at the Present ABI boundary.
    }
}

void on_present_safely(IDXGISwapChain* swap_chain) noexcept
{
    try
    {
        on_present_inner(swap_chain);
    }
    catch (std::exception const& error)
    {
        report_present_failure(error.what());
    }
    catch (...)
    {
        report_present_failure("unknown exception");
    }
}

HRESULT STDMETHODCALLTYPE present_thunk(
    IDXGISwapChain* swap_chain,
    UINT sync_interval,
    UINT flags
) noexcept
{
    on_present_safely(swap_chain);
    // Every per-frame COM reference and command list is released before this call.
    return g_original_present(swap_chain, sync_interval, flags);
}

} // namespace

void install()
{
    if (g_hooked_slot)
    {
        return;
    }

    RE::BSGraphics::Renderer* const renderer = RE::BSGraphics::Renderer::GetSingleton();
    if (!renderer)
    {
        return;
    }

    if (
        !renderer->GetRuntimeData().renderWindows ||
        !renderer->GetRuntimeData().renderWindows[0].swapChain)
    {
        SKSE::log::warn("SwapChain not available yet, Present hook was not installed");
        return;
    }

    IDXGISwapChain* const swap_chain = reinterpret_cast<IDXGISwapChain*>(
        renderer->GetRuntimeData().renderWindows[0].swapChain
    );
    void** const vtable = *reinterpret_cast<void***>(swap_chain);
    void** const present_slot = &vtable[8];

    DWORD old_protection = 0;
    if (!VirtualProtect(present_slot, sizeof(void*), PAGE_READWRITE, &old_protection))
    {
        SKSE::log::error("VirtualProtect failed, Present hook was not installed");
        return;
    }

    g_original_present = reinterpret_cast<Present>(*present_slot);
    *present_slot = reinterpret_cast<void*>(&present_thunk);

    DWORD restored_protection = 0;
    if (!VirtualProtect(present_slot, sizeof(void*), old_protection, &restored_protection))
    {
        SKSE::log::warn("Present hook installed, but vtable page protection could not be restored");
    }
    g_hooked_slot = present_slot;
    SKSE::log::info("Installed IDXGISwapChain::Present hook (swapchain={})", fmt::ptr(swap_chain));
}

void on_present(IDXGISwapChain* swap_chain)
{
    on_present_safely(swap_chain);
}

} // namespace esp_renderer
} // namespace {{PROJECT_NAMESPACE}}
