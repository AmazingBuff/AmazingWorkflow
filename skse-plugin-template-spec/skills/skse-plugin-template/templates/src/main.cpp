//
// Created by AmazingBuff on {{DATE}}.
//

{{FEATURE_INCLUDES}}

#include <filesystem>
#include <memory>
#include <optional>
#include <string>
#include <utility>

namespace
{
    void initialize_log()
    {
        std::optional<std::filesystem::path> path = logger::log_directory();
        if (!path)
            util::report_and_fail("Failed to find standard logging directory"sv);

        *path /= fmt::format("{}.log"sv, Plugin::NAME);
        std::shared_ptr<spdlog::sinks::basic_file_sink_mt> sink = std::make_shared<spdlog::sinks::basic_file_sink_mt>(path->string(), true);

        constexpr static spdlog::level::level_enum s_level = spdlog::level::info;

        std::shared_ptr<spdlog::logger> log = std::make_shared<spdlog::logger>("global log"s, std::move(sink));
        log->set_level(s_level);
        log->flush_on(s_level);

        spdlog::set_default_logger(std::move(log));
        spdlog::set_pattern("%g(%#): [%^%l%$] %v"s);
    }

    void message_handler(SKSE::MessagingInterface::Message* a_msg)
    {
        switch (a_msg->type)
        {
        case SKSE::MessagingInterface::kDataLoaded:
            logger::info("Game data loaded"sv);
            {{ON_DATALOADED}}
            break;
        case SKSE::MessagingInterface::kNewGame:
            logger::info("New game started"sv);
            break;
        case SKSE::MessagingInterface::kPostLoadGame:
            logger::info("Save game loaded"sv);
            break;
        default:
            break;
        }
    }
}

extern "C" DLLEXPORT bool SKSEAPI SKSEPlugin_Load(SKSE::LoadInterface const* a_skse)
{
    REL::Module::reset();  // Clib-NG bug workaround

    initialize_log();
    logger::info("{} v{}"sv, Plugin::NAME, Plugin::VERSION.string());

    SKSE::Init(a_skse);
    if (!SKSE::GetMessagingInterface()->RegisterListener(message_handler))
    {
        logger::critical("Failed to register SKSE message listener"sv);
        return false;
    }

    {{ON_LOAD}}

    logger::info("{} loaded"sv, Plugin::NAME);
    return true;
}
