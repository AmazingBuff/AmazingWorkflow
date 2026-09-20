#pragma once

#include <RE/Skyrim.h>
#include <REL/Relocation.h>
#include <SKSE/SKSE.h>
#include <REX/W32/D3D11.h>
#include <fmt/format.h>

#include <atomic>
#include <cstdint>
#include <cstring>
#include <exception>
#include <filesystem>
#include <memory>
#include <mutex>
#include <string>
#include <string_view>
#include <utility>

using namespace std::literals;
namespace logger = SKSE::log;
#define DLLEXPORT __declspec(dllexport)

#include "Plugin.h"
