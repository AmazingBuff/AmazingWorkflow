//
// Created by AmazingBuff on {{DATE}}.
//

#include "config.h"

#include <SimpleIni.h>

#include <atomic>

namespace
{
    Config::Settings g_settings;
    std::atomic<bool> g_enabled{ true };
}

namespace Config
{

std::filesystem::path get_ini_path() noexcept
{
    // 放在游戏 Data\SKSE\Plugins\ 下，与 DLL 同目录
    auto const exe_path = REL::Module::get().filePath();  // SkyrimSE.exe 的完整路径（wstring_view）
    std::filesystem::path game_root(exe_path);
    return game_root.parent_path() / "Data" / "SKSE" / "Plugins" / (std::string(Plugin::NAME) + ".ini");
}

void load() noexcept
{
    CSimpleIniA ini;
    ini.SetUnicode();

    auto const path = get_ini_path();
    SI_Error const rc = ini.LoadFile(path.string().c_str());
    if (rc < 0)
    {
        logger::info("INI not found at {}, writing defaults", path.string());
    }

    g_settings.enabled = ini.GetBoolValue("General", "Enabled", g_settings.enabled);
    g_settings.hotkey = static_cast<std::uint32_t>(ini.GetLongValue("General", "Hotkey", static_cast<long>(g_settings.hotkey)));
    g_settings.max_distance = static_cast<float>(ini.GetDoubleValue("General", "MaxDistance", g_settings.max_distance));
    g_settings.scan_interval_ms = static_cast<std::uint32_t>(ini.GetLongValue("General", "ScanIntervalMs", static_cast<long>(g_settings.scan_interval_ms)));

    // Read additional project-specific fields here.

    g_enabled.store(g_settings.enabled, std::memory_order_relaxed);

    // 写回，保证文件存在且包含全部选项说明
    save();

    logger::info("Config loaded: enabled={}, hotkey=0x{:02X}", g_settings.enabled, g_settings.hotkey);
}

void save() noexcept
{
    CSimpleIniA ini;
    ini.SetUnicode();
    auto const path = get_ini_path();
    if (ini.LoadFile(path.string().c_str()) < 0)
    {
        logger::info("INI not found at {}, writing defaults", path.string());
    }

    ini.SetBoolValue("General", "Enabled", g_settings.enabled);
    ini.SetLongValue("General", "Hotkey", static_cast<long>(g_settings.hotkey));
    ini.SetDoubleValue("General", "MaxDistance", g_settings.max_distance);
    ini.SetLongValue("General", "ScanIntervalMs", static_cast<long>(g_settings.scan_interval_ms));
    // ... 在此写回其余字段 ...

    SI_Error const save_rc = ini.SaveFile(path.string().c_str());
    if (save_rc < 0)
    {
        logger::warn("Failed to write INI at {}", path.string());
    }
}

void reset_defaults() noexcept
{
    g_settings = Settings{};
    g_enabled.store(g_settings.enabled, std::memory_order_relaxed);
    save();
    logger::info("Config reset to defaults");
}

Settings const& get() noexcept
{
    return g_settings;
}

Settings& get_mutable() noexcept
{
    return g_settings;
}

bool is_enabled() noexcept
{
    return g_enabled.load(std::memory_order_relaxed);
}

void set_enabled(bool a_enabled) noexcept
{
    g_settings.enabled = a_enabled;
    g_enabled.store(a_enabled, std::memory_order_relaxed);
}

void save_enabled() noexcept
{
    CSimpleIniA ini;
    ini.SetUnicode();
    auto const path = get_ini_path();
    if (ini.LoadFile(path.string().c_str()) >= 0)
    {
        ini.SetBoolValue("General", "Enabled", is_enabled());
        SI_Error const save_rc = ini.SaveFile(path.string().c_str());
        if (save_rc < 0)
        {
            logger::warn("Failed to save enabled state to INI at {}", path.string());
        }
    }
}
}
