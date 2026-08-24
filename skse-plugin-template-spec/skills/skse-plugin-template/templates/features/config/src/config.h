//
// Created by AmazingBuff on {{DATE}}.
//

#pragma once

#include <cstdint>
#include <filesystem>

// INI 配置模块（SimpleIni）。
// 用法：main.cpp 的 SKSEPlugin_Load 调用 Config::load()；游戏主线程修改用
// get_mutable()，渲染/读线程经 get() 无锁读取（开关额外经原子 is_enabled()）。
namespace Config
{

struct Settings
{
    bool enabled{ true };                   // 默认启用
    std::uint32_t hotkey{ 0x76 };           // F7
    float max_distance{ 8000.0f };          // 最大作用距离（游戏单位）
    std::uint32_t scan_interval_ms{ 500 };  // 扫描间隔
    // ... 在此按插件需求扩展字段 ...
};

[[nodiscard]] Settings const& get() noexcept;
[[nodiscard]] Settings& get_mutable() noexcept;

[[nodiscard]] bool is_enabled() noexcept;
void set_enabled(bool a_enabled) noexcept;
void save_enabled() noexcept;

void load() noexcept;
void save() noexcept;            // 全量写回 INI（含全部选项说明）
void reset_defaults() noexcept;  // 恢复默认值并写回
[[nodiscard]] std::filesystem::path get_ini_path() noexcept;
}
