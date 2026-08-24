//
// Created by AmazingBuff on {{DATE}}.
//

{{FEATURE_INCLUDES}}

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
            { { ON_DATALOADED } }
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

extern "C" DLLEXPORT bool SKSEAPI SKSEPlugin_Query(SKSE::QueryInterface const* a_skse, SKSE::PluginInfo* a_info)
{
    a_info->infoVersion = SKSE::PluginInfo::kVersion;
    a_info->name = Plugin::NAME.data();
    a_info->version = Plugin::VERSION[0];

    if (a_skse->IsEditor())
    {
        logger::critical("Loaded in editor, marking as incompatible"sv);
        return false;
    }

    REL::Version const runtime = a_skse->RuntimeVersion();
    if (runtime < SKSE::RUNTIME_SSE_1_6_629)
    {
        logger::critical("Unsupported runtime version {}"sv, runtime.string());
        return false;
    }

    return true;
}

extern "C" DLLEXPORT constinit auto SKSEPlugin_Version = []
    {
        SKSE::PluginVersionData v;

        v.PluginVersion(Plugin::VERSION);
        v.PluginName(Plugin::NAME);
        v.AuthorName("{{AUTHOR}}");
        v.UsesAddressLibrary();
        v.UsesNoStructs();
        v.CompatibleVersions({ SKSE::RUNTIME_SSE_LATEST });

        return v;
    }();

extern "C" DLLEXPORT bool SKSEAPI SKSEPlugin_Load(SKSE::LoadInterface const* a_skse)
{
    REL::Module::reset();  // Clib-NG bug workaround

    initialize_log();
    logger::info("{} v{}"sv, Plugin::NAME, Plugin::VERSION.string());

    SKSE::Init(a_skse);
    SKSE::AllocTrampoline(1 << 4);

    SKSE::GetMessagingInterface()->RegisterListener(message_handler);

    { { ON_LOAD } }

    logger::info("{} loaded"sv, Plugin::NAME);
    return true;
}
