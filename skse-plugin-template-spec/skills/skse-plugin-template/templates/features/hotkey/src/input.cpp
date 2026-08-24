//
// Created by AmazingBuff on {{DATE}}.
//

#include "input.h"
#include "config.h"

namespace
{
    bool g_was_down = false;
}

namespace Input
{

void poll()
{
    auto const vk = Config::get().hotkey;
    if (vk == 0)
    {
        return;
    }

    bool const down = (GetAsyncKeyState(static_cast<int>(vk)) & 0x8000) != 0;
    if (down && !g_was_down)
    {
        bool const enabled = !Config::is_enabled();
        Config::set_enabled(enabled);
        // 控制台消息与 INI 写回放到游戏线程执行（Print 为 printf 风格）
        SKSE::GetTaskInterface()->AddTask([enabled]() {
            auto const msg = fmt::format("{}: {}", Plugin::NAME, enabled ? "ON" : "OFF");
            RE::ConsoleLog::GetSingleton()->Print("%s", msg.c_str());
            Config::save_enabled();
        });
    }
    g_was_down = down;
}
}
