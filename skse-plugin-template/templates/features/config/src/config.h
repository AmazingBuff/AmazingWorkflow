//
// Created by AmazingBuff on {{DATE}}.
//

#pragma once

#include <cstdint>
#include <filesystem>

namespace {{PROJECT_NAMESPACE}}
{
namespace config
{

struct Settings
{
    bool enabled{ true };
    std::uint32_t hotkey{ 0x76 };
    float max_distance{ 8000.0f }; // Skyrim game units.
    std::uint32_t scan_interval_ms{ 500 };
    // Add project-specific persisted settings here.
};

// Callers receive a coherent copy and never borrow mutable configuration state.
[[nodiscard]] Settings get_snapshot();

[[nodiscard]] bool is_enabled() noexcept;
[[nodiscard]] std::uint32_t get_hotkey() noexcept;
void set_enabled(bool enabled) noexcept;
void save_enabled();

void load();
void save();
void reset_defaults();
[[nodiscard]] std::filesystem::path get_ini_path();

} // namespace config
} // namespace {{PROJECT_NAMESPACE}}
