{{FEATURE_INCLUDES}}

#include <spdlog/sinks/basic_file_sink.h>

namespace
{
    void initialize_log()
    {
        auto path = logger::log_directory();
        if (!path)
            SKSE::stl::report_and_fail("Failed to find standard logging directory"sv);
        *path /= fmt::format("{}.log", Plugin::Plugin_Name);
        auto sink = std::make_shared<spdlog::sinks::basic_file_sink_mt>(path->string(), true);
        auto log = std::make_shared<spdlog::logger>("global log", std::move(sink));
        log->set_level(spdlog::level::info);
        log->flush_on(spdlog::level::info);
        spdlog::set_default_logger(std::move(log));
        spdlog::set_pattern("%g(%#): [%^%l%$] %v");
    }

    void message_handler(SKSE::MessagingInterface::Message* a_msg) noexcept
    {
        if (!a_msg)
            return;
        try
        {
            switch (a_msg->type)
            {
            case SKSE::MessagingInterface::kDataLoaded:
                {{ON_DATALOADED}}
                break;
            case SKSE::MessagingInterface::kNewGame:
            case SKSE::MessagingInterface::kPostLoadGame:
                {{ON_GAME_READY}}
                break;
            case SKSE::MessagingInterface::kSaveGame:
                {{ON_SAVE}}
                break;
            default:
                break;
            }
        }
        catch (...)
        {
            try { logger::error("Plugin message handler failed"); } catch (...) {}
        }
    }
}

extern "C" DLLEXPORT bool SKSEPlugin_Load(SKSE::LoadInterface const* a_skse) noexcept
{
    try
    {
        REL::Module::reset(); // Reference project's CommonLib workaround; reassess on upgrade.
        initialize_log();
        logger::info("{} v{}", Plugin::Plugin_Name, Plugin::Plugin_Version.string());
        SKSE::Init(a_skse);
        {{ON_LOAD}}
        auto* messaging = SKSE::GetMessagingInterface();
        if (!messaging || !messaging->RegisterListener(message_handler))
            return false;
        logger::info("{} loaded", Plugin::Plugin_Name);
        return true;
    }
    catch (...)
    {
        try { logger::critical("SKSEPlugin_Load failed"); } catch (...) {}
        return false;
    }
}

extern "C" DLLEXPORT constinit auto SKSEPlugin_Version = [] {
    SKSE::PluginVersionData v;
    v.PluginVersion(Plugin::Plugin_Version);
    v.PluginName(Plugin::Plugin_Name);
    v.AuthorName(Plugin::Plugin_Author);
    v.UsesAddressLibrary();
    v.UsesNoStructs();
    return v;
}();

extern "C" DLLEXPORT bool SKSEPlugin_Query(SKSE::QueryInterface const* a_skse, SKSE::PluginInfo* a_info)
{
    if (!a_skse || !a_info || a_skse->IsEditor())
        return false;
    a_info->infoVersion = SKSE::PluginInfo::kVersion;
    a_info->name = SKSEPlugin_Version.pluginName;
    a_info->version = SKSEPlugin_Version.pluginVersion;
    return true;
}
