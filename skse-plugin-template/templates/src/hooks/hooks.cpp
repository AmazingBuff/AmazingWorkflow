#include "hooks.h"
PLUGIN_NAMESPACE_BEGIN
namespace
{
    using Update = void (*)(RE::Actor*, float);
    std::atomic<Update> g_ref_update{ nullptr };
    void update_thunk(RE::Actor* a_actor, float a_delta)
    {
        g_ref_update.load(std::memory_order_acquire)(a_actor, a_delta);
    }
}
void Hooks::install()
{
    if (g_ref_update.load(std::memory_order_acquire))
        return;
    // Flat-header example: verify slot/signature in every target executable.
    constexpr std::size_t Update_Slot = 0xAD;
    REL::Relocation<uintptr_t> vtable{ RE::VTABLE_Character[0] };
    auto* table = reinterpret_cast<uintptr_t const*>(vtable.address());
    g_ref_update.store(reinterpret_cast<Update>(table[Update_Slot]), std::memory_order_release);
    vtable.write_vfunc(Update_Slot, &update_thunk);
}
PLUGIN_NAMESPACE_END
