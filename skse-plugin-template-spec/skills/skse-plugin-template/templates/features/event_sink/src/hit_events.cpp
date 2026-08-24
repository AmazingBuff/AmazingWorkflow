//
// Created by AmazingBuff on {{DATE}}.
//

#include "hit_events.h"

namespace
{

class HitSink final : public RE::BSTEventSink<RE::TESHitEvent>
{
public:
    RE::BSEventNotifyControl ProcessEvent(RE::TESHitEvent const* a_event, RE::BSTEventSource<RE::TESHitEvent>* a_source) override
    {
        // ... 在此实现受击兜底逻辑（事件在主线程执行）...
        return RE::BSEventNotifyControl::kContinue;
    }
};

// sink 与进程同生命周期；用静态对象避免裸 new（引擎侧不持有所有权）
HitSink g_sink;

}

namespace HitEvents
{

void install()
{
    auto* holder = RE::ScriptEventSourceHolder::GetSingleton();
    if (!holder)
    {
        logger::error("ScriptEventSourceHolder unavailable, TESHitEvent sink not installed"sv);
        return;
    }
    holder->AddEventSink<RE::TESHitEvent>(&g_sink);
    logger::info("Installed TESHitEvent sink"sv);
}
}
