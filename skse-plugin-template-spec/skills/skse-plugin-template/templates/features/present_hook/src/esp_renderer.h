//
// Created by AmazingBuff on {{DATE}}.
//

#pragma once

#include <d3d11.h>
#include <dxgi.h>

// D3D11 Present 钩子 + DirectXTK 绘制模块。
// 用法：kDataLoaded 后调用 ESPRenderer::install()（幂等）；on_present 在每次
// IDXGISwapChain::Present 前绘制（可在此调用 Input::poll() 轮询热键）。
namespace ESPRenderer
{

// 在游戏线程上调用（渲染器初始化之后），安装 IDXGISwapChain::Present 钩子；幂等
void install();

// 渲染线程：每次 Present 前调用，绘制覆盖层
void on_present(IDXGISwapChain* a_swap_chain);
}
