# 可复用代码模式

> 以下模式提取自 CorpseESP（配置/热键/渲染/菜单）与 FollowerSummonAllyFix
> （钩子/事件/阵营）。每个模式对应一个命名空间 + h/cpp 对，代码可直接作为新模块蓝本。

## 0. 头文件开头与 include 顺序

- 源文件无需显式包含 `pch.h`（`target_precompile_headers` 已强制注入）；随后同项目头、
  第三方头、标准库头。
- 头文件 `#pragma once`；类/枚举用 `PascalCase`，函数/变量 `snake_case`，
  east const（`Type const&`），4 空格、Allman 大括号（遵循本 skill 内置的
  `assets/coding-rules/small-project-cpp-rules` 组件）。

> 本文件代码为模式示意；权威模板以 `templates/` 内对应文件为准。

## 1. 预编译头 pch.h

```cpp
#pragma once
#include <RE/Skyrim.h>
#include <REL/Relocation.h>
#include <SKSE/SKSE.h>
#include <fmt/format.h>
#include <spdlog/sinks/basic_file_sink.h>
#include <spdlog/sinks/msvc_sink.h>

using namespace std::literals;
namespace logger = SKSE::log;
namespace util { using SKSE::stl::report_and_fail; }
#define DLLEXPORT __declspec(dllexport)
#include "Plugin.h"
```

> 第三方功能头（如 `<SimpleIni.h>`）尽量只在对应 `.cpp` 中引入，保持 PCH 稳定；
> 若该依赖被广泛使用再提升到 PCH。

## 2. 插件入口 main.cpp

- `initialize_log()`：`logger::log_directory()` → `<Plugin::NAME>.log`，
  `spdlog::basic_file_sink_mt`，pattern `"%g(%#): [%^%l%$] %v"`。
- `message_handler(SKSE::MessagingInterface::Message*)`：`kDataLoaded` /
  `kNewGame` / `kPostLoadGame` 分发。
- `SKSEPlugin_Query` / `SKSEPlugin_Version` / `SKSEPlugin_Load` 见
  [multi-runtime.md](multi-runtime.md) §3–5。
- `SKSEPlugin_Load` 中 `REL::Module::reset()` 后初始化日志、`SKSE::Init`、
  `AllocTrampoline`（需要时）、注册消息监听、安装各功能钩子。

## 3. INI 配置（Config，SimpleIni）

```cpp
// config.h
namespace Config 
{
    struct Settings { bool enabled{ true }; /* ... */ };
    [[nodiscard]] Settings const& get() noexcept;          // 渲染/读线程无锁读取
    [[nodiscard]] Settings& get_mutable() noexcept;        // 主线程修改
    [[nodiscard]] bool is_enabled() noexcept;
    void set_enabled(bool a_enabled) noexcept;
    void load() noexcept;
    void save() noexcept;
    void reset_defaults() noexcept;
    [[nodiscard]] std::filesystem::path get_ini_path() noexcept;
}
```

- `get_ini_path()`：`REL::Module::get().filePath()` → 游戏根目录 →
  `Data/SKSE/Plugins/<Plugin::NAME>.ini`（与 DLL 同目录）。
- `load()`：`CSimpleIniA` 读入 + 默认值兜底 + `save()` 写回（保证文件存在且含全部选项说明）。
- 线程模型：主线程经 `get_mutable()` 修改；渲染线程经 `get()` 无锁读取；开关用
  `std::atomic<bool>`。

## 4. 热键轮询（Input，GetAsyncKeyState）

```cpp
namespace Input { void poll(); }   // 每帧从渲染回调调用
```

```cpp
bool const down = (GetAsyncKeyState(static_cast<int>(vk)) & 0x8000) != 0;
if (down && !g_was_down) 
{   // 边沿触发
    Config::set_enabled(!Config::is_enabled());
    SKSE::GetTaskInterface()->AddTask([enabled] 
    {   // 控制台/INI 写回到游戏线程
        RE::ConsoleLog::GetSingleton()->Print(...);
        Config::save_enabled();
    });
}
g_was_down = down;
```

## 5. D3D11 Present 钩子（ESPRenderer，DirectXTK）

```cpp
namespace ESPRenderer 
{
    void install();                 // 游戏线程、渲染器初始化后调用；幂等
    void on_present(IDXGISwapChain* a_swapChain);   // 每次 Present 前绘制
}
```

- 钩住 `IDXGISwapChain` vtable 第 8 槽位（Present，与运行时版本无关）。
- 用 DirectXTK `BasicEffect` + `PrimitiveBatch` 绘制；绘制期间关闭深度测试/背面剔除、
  开启 Alpha 混合，绘制后恢复 RenderTarget/Blend/Depth/Rasterizer 状态。
- 热键 `Input::poll()` 在 `on_present` 中调用（CorpseESP 模式）。

## 6. vtable 钩子（Hooks，多运行时）

```cpp
// hooks.cpp
using Update_t = void (*)(RE::Actor*, float);
static inline Update_t g_update = nullptr;

static void hook_update(RE::Actor* a_this, float a_delta)
{
    // ...每帧处理...
    update(a_this, a_delta);
}

void install()
{
    constexpr static std::size_t s_index = 0xAD;                       // Character::Update
    REL::Relocation<std::uintptr_t> vtable{ RE::VTABLE_Character[0] };
    g_update = reinterpret_cast<Update_t>(vtable.write_vfunc(s_index, hook_update));
}
```

- 槽位 `0xAD` 与 True Directional Movement 一致，跨 SE/AE/VR 稳定（已验证）。

## 7. 事件监听（HitEvents，TESHitEvent sink）

```cpp
// hit_events.cpp
class HitSink final : public RE::BSTEventSink<RE::TESHitEvent>
{
public:
    RE::BSEventNotifyControl ProcessEvent(RE::TESHitEvent const* a_event, RE::BSTEventSource<RE::TESHitEvent>* a_source) override;
};

void install()
{
    RE::ScriptEventSourceHolder::GetSingleton()->AddEventSink<RE::TESHitEvent>(new HitSink());
}
```

- 事件回调在游戏主线程执行；用于"受击兜底"类即时响应。

## 8. 引擎数据查找（FormID / 阵营缓存）

```cpp
auto const form = RE::TESDataHandler::GetSingleton()->LookupForm(formID, "Skyrim.esm");
return form ? form->As<RE::TESFaction>() : nullptr;
```

- 在 `kDataLoaded` 后调用并缓存到静态指针；后续 getter 直接返回。
- 用 FormID（如 `PlayerAllyFaction` = `0x5C84C`）而非硬编码 EditorID 字符串。

## 9. 生命周期接线汇总

| 时机 | 做什么 |
|------|--------|
| `SKSEPlugin_Load` | 日志、`SKSE::Init`、`Config::load()`、`Hooks::install()`、`HitEvents::install()` |
| `message_handler(kDataLoaded)` | 数据查找初始化、`ESPRenderer::install()`、MCP 面板注册、存量对象处理 |
| `kNewGame` / `kPostLoadGame` | 存量对象重扫/重初始化 |
| 每帧（hook / on_present） | `Input::poll()`、每帧净化等 |

## 10. 错误与日志

- 不可恢复问题用 `util::report_and_fail(...)`（映射到 SKSE 的 report_and_fail）。
- 常规日志走 `logger::info/error/warn/critical`，pattern 已含源文件行号。
- 外部边界（INI 读、事件注册）失败要记日志并给出可恢复行为，不静默吞掉。
