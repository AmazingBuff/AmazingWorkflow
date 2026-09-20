#include "hit_events.h"
PLUGIN_NAMESPACE_BEGIN
namespace
{
    class HitHandler final : public RE::BSTEventSink<RE::TESHitEvent>
    {
    public:
        RE::BSEventNotifyControl ProcessEvent(RE::TESHitEvent const*,
            RE::BSTEventSource<RE::TESHitEvent>*) noexcept override
        {
            // Add project hit behavior here without retaining borrowed event pointers.
            return RE::BSEventNotifyControl::kContinue;
        }
    };
}
void HitEvents::install()
{
    static HitHandler s_handler;
    static bool s_installed = false;
    if (s_installed)
        return;
    auto* source = RE::ScriptEventSourceHolder::GetSingleton();
    if (!source)
        return;
    source->AddEventSink<RE::TESHitEvent>(&s_handler);
    s_installed = true;
}
PLUGIN_NAMESPACE_END
