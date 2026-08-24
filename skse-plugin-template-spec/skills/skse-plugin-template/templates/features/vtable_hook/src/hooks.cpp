//
// Created by AmazingBuff on {{DATE}}.
//

#include "hooks.h"

namespace Hooks
{

using Update_t = void (*)(RE::Actor*, float);

// 原槽位函数指针；命名空间级 static（内部链接），仅 install() 写入、钩子内调用
Update_t g_update = nullptr;

void hook_update(RE::Actor* a_this, float a_delta)
{
    // ... 每帧处理（替换为插件实际逻辑；注意保持开销 O(1)/早退）...
    g_update(a_this, a_delta);
}

void install()
{
    constexpr std::size_t Character_Update_Slot = 0xAD;

    // 多运行时：RE::VTABLE_Character[0] 由地址库提供 SE/AE/VR 三个地址
    REL::Relocation<std::uintptr_t> characterVtbl{ RE::VTABLE_Character[0] };
    g_update = reinterpret_cast<Update_t>(characterVtbl.write_vfunc(Character_Update_Slot, hook_update));

    logger::info("Installed Character::Update hook at vtable slot 0x{:X} (multi-runtime SE/AE/VR)"sv, Character_Update_Slot);
}
}
