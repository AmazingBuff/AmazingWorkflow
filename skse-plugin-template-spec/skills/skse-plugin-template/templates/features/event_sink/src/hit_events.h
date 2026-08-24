//
// Created by AmazingBuff on {{DATE}}.
//

#pragma once

// SKSE 事件监听模块：TESHitEvent 示例 sink。
// 用法：SKSEPlugin_Load 中调用 HitEvents::install()；事件回调运行在游戏主线程。
namespace HitEvents
{

void install();
}
