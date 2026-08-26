//
// Created by AmazingBuff on {{DATE}}.
//

#include "hooks.h"

#include <cstddef>
#include <cstdint>

namespace {{PROJECT_NAMESPACE}}
{
namespace hooks
{
namespace
{

using Update = void (*)(RE::Actor*, float);

Update g_update = nullptr;

void hook_update(RE::Actor* actor, float delta)
{
    // Add constant-time per-frame plugin behavior before delegating to the ABI original.
    g_update(actor, delta);
}

} // namespace

void install()
{
    static constexpr std::size_t s_character_update_slot = 0xAD;

    // CommonLib resolves this vtable for every enabled SE, AE, and VR runtime.
    REL::Relocation<std::uintptr_t> character_vtable{ RE::VTABLE_Character[0] };
    g_update = reinterpret_cast<Update>(
        character_vtable.write_vfunc(s_character_update_slot, hook_update)
    );

    SKSE::log::info(
        "Installed Character::Update hook at vtable slot 0x{:X} (multi-runtime SE/AE/VR)",
        s_character_update_slot
    );
}

} // namespace hooks
} // namespace {{PROJECT_NAMESPACE}}
