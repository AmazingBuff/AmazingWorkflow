//
// Created by AmazingBuff on {{DATE}}.
//

#include "hit_events.h"

namespace {{PROJECT_NAMESPACE}}
{
namespace hit_events
{
namespace
{

class HitSink final : public RE::BSTEventSink<RE::TESHitEvent>
{
public:
    RE::BSEventNotifyControl ProcessEvent(
        RE::TESHitEvent const*,
        RE::BSTEventSource<RE::TESHitEvent>*
    ) noexcept override
    {
        // Add game-thread hit handling here without retaining borrowed event pointers.
        return RE::BSEventNotifyControl::kContinue;
    }
};

// The event source borrows this process-lifetime sink and never owns it.
HitSink g_sink;

} // namespace

void install()
{
    RE::ScriptEventSourceHolder* const event_source =
        RE::ScriptEventSourceHolder::GetSingleton();
    if (!event_source)
    {
        SKSE::log::error("ScriptEventSourceHolder unavailable, TESHitEvent sink not installed");
        return;
    }
    event_source->AddEventSink<RE::TESHitEvent>(&g_sink);
    SKSE::log::info("Installed TESHitEvent sink");
}

} // namespace hit_events
} // namespace {{PROJECT_NAMESPACE}}
