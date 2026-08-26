//
// Created by AmazingBuff on {{DATE}}.
//

#include "input.h"

#include "config.h"
#include "plugin.h"

#include <exception>
#include <string>
#include <string_view>

namespace {{PROJECT_NAMESPACE}}
{
namespace
{

bool g_was_down = false;

void report_input_failure(std::string_view reason) noexcept
{
    try
    {
        SKSE::log::error("Hotkey task failed: {}", reason);
    }
    catch (...)
    {
        // Diagnostics are best-effort while containing exceptions at the task boundary.
    }
}

void apply_toggle_on_game_thread(bool enabled) noexcept
{
    try
    {
        std::string const message = fmt::format(
            "{}: {}",
            plugin::Name,
            enabled ? "ON" : "OFF"
        );
        RE::ConsoleLog::GetSingleton()->Print("%s", message.c_str());
        config::save_enabled();
    }
    catch (std::exception const& error)
    {
        report_input_failure(error.what());
    }
    catch (...)
    {
        report_input_failure("unknown exception");
    }
}

} // namespace

namespace input
{

void poll()
{
    std::uint32_t const virtual_key = config::get_hotkey();
    if (virtual_key == 0)
    {
        return;
    }

    bool const down = (GetAsyncKeyState(static_cast<int>(virtual_key)) & 0x8000) != 0;
    if (down && !g_was_down)
    {
        bool const enabled = !config::is_enabled();
        config::set_enabled(enabled);
        // Console output and file I/O are deferred to the game thread.
        SKSE::GetTaskInterface()->AddTask(
            [enabled]() noexcept
            {
                apply_toggle_on_game_thread(enabled);
            }
        );
    }
    g_was_down = down;
}

} // namespace input
} // namespace {{PROJECT_NAMESPACE}}
