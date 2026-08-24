//
// Created by AmazingBuff on {{DATE}}.
//

#pragma once

#include <RE/Skyrim.h>
#include <REL/Relocation.h>
#include <SKSE/SKSE.h>
#include <fmt/format.h>
#include <spdlog/sinks/basic_file_sink.h>
#include <spdlog/sinks/msvc_sink.h>

using namespace std::literals;

namespace logger = SKSE::log;

namespace util
{
    using SKSE::stl::report_and_fail;
}

#define DLLEXPORT __declspec(dllexport)

#include "Plugin.h"
