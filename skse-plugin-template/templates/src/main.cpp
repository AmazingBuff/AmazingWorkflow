//
// Created by AmazingBuff on {{DATE}}.
//

{{FEATURE_INCLUDES}}

#include <exception>
#include <filesystem>
#include <memory>
#include <optional>
#include <string>
#include <string_view>
#include <utility>

namespace {{PROJECT_NAMESPACE}}
{
namespace
{

void initialize_log()
{
    std::optional<std::filesystem::path> path = SKSE::log::log_directory();
    if (!path)
        SKSE::stl::report_and_fail("Failed to find standard logging directory");

    *path /= fmt::format("{}.log", plugin::Name);
    std::shared_ptr<spdlog::sinks::basic_file_sink_mt> sink =
        std::make_shared<spdlog::sinks::basic_file_sink_mt>(path->string(), true);

    static constexpr spdlog::level::level_enum s_level = spdlog::level::info;

    std::shared_ptr<spdlog::logger> log =
        std::make_shared<spdlog::logger>("global log", std::move(sink));
    log->set_level(s_level);
    log->flush_on(s_level);

    spdlog::set_default_logger(std::move(log));
    spdlog::set_pattern("%g(%#): [%^%l%$] %v");
}

void report_boundary_failure(std::string_view operation, std::string_view reason) noexcept
{
    try
    {
        SKSE::log::critical("{} failed: {}", operation, reason);
    }
    catch (...)
    {
        // Diagnostics are best-effort while containing exceptions at an external ABI boundary.
    }
}

void handle_message(SKSE::MessagingInterface::Message* message)
{
    switch (message->type)
    {
    case SKSE::MessagingInterface::kDataLoaded:
        SKSE::log::info("Game data loaded");
        {{ON_DATALOADED}}
        break;
    case SKSE::MessagingInterface::kNewGame:
        SKSE::log::info("New game started");
        break;
    case SKSE::MessagingInterface::kPostLoadGame:
        SKSE::log::info("Save game loaded");
        break;
    default:
        break;
    }
}

void message_handler(SKSE::MessagingInterface::Message* message) noexcept
{
    try
    {
        handle_message(message);
    }
    catch (std::exception const& error)
    {
        report_boundary_failure("SKSE message handler", error.what());
    }
    catch (...)
    {
        report_boundary_failure("SKSE message handler", "unknown exception");
    }
}

} // namespace
} // namespace {{PROJECT_NAMESPACE}}

extern "C" DLLEXPORT bool SKSEAPI SKSEPlugin_Load(SKSE::LoadInterface const* skse) noexcept
{
    try
    {
        // CommonLibSSE-NG requires this reset before SKSE initialization.
        REL::Module::reset();

        {{PROJECT_NAMESPACE}}::initialize_log();
        SKSE::log::info(
            "{} v{}",
            {{PROJECT_NAMESPACE}}::plugin::Name,
            {{PROJECT_NAMESPACE}}::plugin::Version.string()
        );

        SKSE::Init(skse);
        bool const listener_registered = SKSE::GetMessagingInterface()->RegisterListener(
            {{PROJECT_NAMESPACE}}::message_handler
        );
        if (!listener_registered)
        {
            SKSE::log::critical("Failed to register SKSE message listener");
            return false;
        }

        {{ON_LOAD}}

        SKSE::log::info("{} loaded", {{PROJECT_NAMESPACE}}::plugin::Name);
        return true;
    }
    catch (std::exception const& error)
    {
        {{PROJECT_NAMESPACE}}::report_boundary_failure("SKSEPlugin_Load", error.what());
        return false;
    }
    catch (...)
    {
        {{PROJECT_NAMESPACE}}::report_boundary_failure("SKSEPlugin_Load", "unknown exception");
        return false;
    }
}
