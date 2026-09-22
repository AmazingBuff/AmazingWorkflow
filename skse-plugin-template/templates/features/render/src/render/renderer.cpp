#include "renderer.h"
#include "present_hook.h"

PLUGIN_NAMESPACE_BEGIN

namespace
{
    class OverlayDirector
    {
    public:
        static OverlayDirector& instance()
        {
            static OverlayDirector s_instance;
            return s_instance;
        }

        void on_present(REX::W32::IDXGISwapChain* swap_chain)
        {
            std::unique_lock draw_lock(m_draw_mutex, std::try_to_lock);
            if (!draw_lock.owns_lock() || !swap_chain)
                return;
            RE::BSGraphics::Renderer* renderer = RE::BSGraphics::Renderer::GetSingleton();
            if (!renderer)
                return;
            auto& runtime = renderer->GetRuntimeData();
            if (!runtime.forwarder || !runtime.context)
                return;
            draw(swap_chain, runtime.forwarder, runtime.context);
        }
    private:
        OverlayDirector() = default;

    private:
        void draw([[maybe_unused]] REX::W32::IDXGISwapChain* swap_chain,
            [[maybe_unused]] REX::W32::ID3D11Device* device,
            [[maybe_unused]] REX::W32::ID3D11DeviceContext* context)
        {
            // Add project render passes here. No pipeline state is changed by the skeleton.
            // Use D3D11StateCapture around writes; extend its captured states for new passes.
        }
        std::mutex m_draw_mutex;
    };

    void present_callback(REX::W32::IDXGISwapChain* swap_chain)
    {
        OverlayDirector::instance().on_present(swap_chain);
    }
}

void Renderer::install()
{
    (void)PresentHook::instance().install(&present_callback);
}

PLUGIN_NAMESPACE_END
