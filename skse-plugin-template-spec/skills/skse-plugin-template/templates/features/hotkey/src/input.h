//
// Created by AmazingBuff on {{DATE}}.
//

#pragma once

// 热键模块：每帧从渲染回调（或 vtable 钩子）调用 Input::poll()，轮询开关热键。
// 依赖 config 模块（读取 Config::get().hotkey）。
namespace Input
{

void poll();
}
