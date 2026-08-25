//
// Created by AmazingBuff on {{DATE}}.
//

#pragma once

// 热键模块：每帧由 present_hook 调用 Input::poll()，轮询开关热键。
// 同时依赖 config 与 present_hook 模块。
namespace Input
{

void poll();
}
