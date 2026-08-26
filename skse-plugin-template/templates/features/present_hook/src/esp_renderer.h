//
// Created by AmazingBuff on {{DATE}}.
//

#pragma once

#include <d3d11.h>
#include <dxgi.h>

namespace {{PROJECT_NAMESPACE}}
{
namespace esp_renderer
{

// Call from the game thread after renderer initialization; installation is idempotent.
void install();

// Call only from the render thread immediately before IDXGISwapChain::Present.
void on_present(IDXGISwapChain* swap_chain);

} // namespace esp_renderer
} // namespace {{PROJECT_NAMESPACE}}
