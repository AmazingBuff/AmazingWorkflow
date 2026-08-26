//
// Created by AmazingBuff on {{DATE}}.
//

#include "config.h"
#include "plugin.h"

#include <SimpleIni.h>

#include <atomic>
#include <mutex>
#include <string>
#include <string_view>

namespace {{PROJECT_NAMESPACE}}
{
namespace
{

config::Settings g_settings;
std::mutex g_settings_mutex;
std::atomic<bool> g_enabled{ true };
std::atomic<std::uint32_t> g_hotkey{ 0x76 };

void publish_render_settings(config::Settings const& settings) noexcept
{
    g_enabled.store(settings.enabled, std::memory_order_relaxed);
    g_hotkey.store(settings.hotkey, std::memory_order_relaxed);
}

void replace_settings(config::Settings const& settings)
{
    std::lock_guard<std::mutex> lock(g_settings_mutex);
    g_settings = settings;
    publish_render_settings(settings);
}

} // namespace

namespace config
{

std::filesystem::path get_ini_path()
{
    std::wstring_view const executable_path = REL::Module::get().filePath();
    std::filesystem::path const game_root(executable_path);
    return game_root.parent_path() / "Data" / "SKSE" / "Plugins" /
        (std::string(plugin::Name) + ".ini");
}

void load()
{
    CSimpleIniA ini;
    ini.SetUnicode();

    std::filesystem::path const path = get_ini_path();
    std::string const path_string = path.string();
    SI_Error const load_result = ini.LoadFile(path_string.c_str());
    if (load_result < 0)
    {
        SKSE::log::info("INI not found at {}, writing defaults", path_string);
    }

    Settings settings;
    settings.enabled = ini.GetBoolValue("General", "Enabled", settings.enabled);
    settings.hotkey = static_cast<std::uint32_t>(
        ini.GetLongValue("General", "Hotkey", static_cast<long>(settings.hotkey))
    );
    settings.max_distance = static_cast<float>(
        ini.GetDoubleValue("General", "MaxDistance", settings.max_distance)
    );
    settings.scan_interval_ms = static_cast<std::uint32_t>(
        ini.GetLongValue(
            "General",
            "ScanIntervalMs",
            static_cast<long>(settings.scan_interval_ms)
        )
    );

    // Read additional project-specific fields into settings here.

    replace_settings(settings);
    save();

    SKSE::log::info("Config loaded: enabled={}, hotkey=0x{:02X}", settings.enabled, settings.hotkey);
}

void save()
{
    CSimpleIniA ini;
    ini.SetUnicode();
    std::filesystem::path const path = get_ini_path();
    std::string const path_string = path.string();
    if (ini.LoadFile(path_string.c_str()) < 0)
    {
        SKSE::log::info("INI not found at {}, writing defaults", path_string);
    }

    Settings const settings = get_snapshot();
    ini.SetBoolValue("General", "Enabled", settings.enabled);
    ini.SetLongValue("General", "Hotkey", static_cast<long>(settings.hotkey));
    ini.SetDoubleValue("General", "MaxDistance", settings.max_distance);
    ini.SetLongValue("General", "ScanIntervalMs", static_cast<long>(settings.scan_interval_ms));
    // Write additional project-specific fields here.

    SI_Error const save_result = ini.SaveFile(path_string.c_str());
    if (save_result < 0)
    {
        SKSE::log::warn("Failed to write INI at {}", path_string);
    }
}

void reset_defaults()
{
    Settings const settings;
    replace_settings(settings);
    save();
    SKSE::log::info("Config reset to defaults");
}

Settings get_snapshot()
{
    std::lock_guard<std::mutex> lock(g_settings_mutex);
    Settings settings = g_settings;
    settings.enabled = g_enabled.load(std::memory_order_relaxed);
    return settings;
}

bool is_enabled() noexcept
{
    return g_enabled.load(std::memory_order_relaxed);
}

std::uint32_t get_hotkey() noexcept
{
    return g_hotkey.load(std::memory_order_relaxed);
}

void set_enabled(bool enabled) noexcept
{
    g_enabled.store(enabled, std::memory_order_relaxed);
}

void save_enabled()
{
    CSimpleIniA ini;
    ini.SetUnicode();
    std::filesystem::path const path = get_ini_path();
    std::string const path_string = path.string();
    if (ini.LoadFile(path_string.c_str()) < 0)
    {
        SKSE::log::info("INI not found at {}, writing enabled state", path_string);
    }
    ini.SetBoolValue("General", "Enabled", is_enabled());
    SI_Error const save_result = ini.SaveFile(path_string.c_str());
    if (save_result < 0)
    {
        SKSE::log::warn("Failed to save enabled state to INI at {}", path_string);
    }
}

} // namespace config
} // namespace {{PROJECT_NAMESPACE}}
