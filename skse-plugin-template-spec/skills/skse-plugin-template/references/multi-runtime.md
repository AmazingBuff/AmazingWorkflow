# SE / AE / VR 多运行时机制

> 核心事实：CommonLibSSE（NG / CommonLibVR 的 ng 分支）支持单 DLL 在多个 Skyrim
> 运行时上工作——运行时在加载时经 **Address Library** 解析，地址/虚表一律走
> `REL::Relocation`，不硬编码单一版本地址。

## 1. 构建期开关

根 CMakeLists.txt 的三个 `option` 决定这一份 DLL 编译进哪些运行时支持：

| 组合 | 含义 |
|------|------|
| `ENABLE_SKYRIM_SE` / `ENABLE_SKYRIM_AE` | 常见 flatrim（SE+AE）单 DLL |
| `ENABLE_SKYRIM_VR` | 加入 VR 支持 |
| 三者全开 | "all" 单 DLL（CorpseESP 默认 SE+AE，FollowerSummonAllyFix 默认全开） |

- 至少开启一个运行时，否则 CMake `FATAL_ERROR`。
- 预处理器定义（CommonLibSSE 消费方视角）：
  - `EXCLUSIVE_SKYRIM_FLAT`：仅 SE/AE（无 VR）
  - `EXCLUSIVE_SKYRIM_VR`：仅 VR
  - `SKYRIM_CROSS_VR`：VR 与 SE/AE 同时开启（多运行时）
- 涉及虚表/布局差异的代码用三段式条件编译 + `REL::RelocateVirtual` / `REL::RelocateMember`
  做运行时探测；无差异路径直接使用地址库。

## 2. 加载期地址解析（Address Library）

```cpp
// 多运行时虚表地址：RE::VTABLE_Character[0] 由地址库提供 SE/AE/VR 三个地址
REL::Relocation<std::uintptr_t> vtable{ RE::VTABLE_Character[0] };
```

- 地址/ID 一律 `REL::Relocation<T>` 包装；运行时不同时在加载时解析到正确地址。
- vtable 钩子：`REL::Relocation<std::uintptr_t> vt{ RE::VTABLE_Xxx[0] }` +
  `vt.write_vfunc(slotIndex, hookFn)`，返回原函数指针。
- 函数地址：`REL::Relocation<FnPtr>{ REL::ID(offse_id) }`（`RELOCATION_ID(se, ae[, vr])`
  宏也可用）。
- `REL::Module::IsVR()` / `IsAE()` 用于运行时探测。

## 3. SKSE 版本数据（SKSE 2.2.x 必需）

```cpp
extern "C" DLLEXPORT constinit auto SKSEPlugin_Version = [] {
    SKSE::PluginVersionData v;
    v.PluginVersion(Plugin::VERSION);
    v.PluginName(Plugin::NAME);
    v.AuthorName("<Author>");
    v.UsesAddressLibrary();                 // 关键：使用地址库 → 跨运行时适配
    v.UsesNoStructs();
    v.CompatibleVersions({ SKSE::RUNTIME_SSE_LATEST });
    return v;
}();
```

- 缺少 `SKSEPlugin_Version` 导出会在 "checking plugin" 阶段被跳过。
- `UsesAddressLibrary()` 表示插件依赖 Address Library（Nexus 32444 / VR 版），
  由用户安装；插件本身不内置版本表。

## 4. 运行时版本检查（SKSEPlugin_Query）

```cpp
extern "C" DLLEXPORT bool SKSEAPI SKSEPlugin_Query(SKSE::QueryInterface const* a_skse, SKSE::PluginInfo* a_info)
{
    a_info->infoVersion = SKSE::PluginInfo::kVersion;
    a_info->name = Plugin::NAME.data();
    a_info->version = Plugin::VERSION[0];

    if (a_skse->IsEditor()) { /* 编辑器环境：返回 false */ }

    if (a_skse->RuntimeVersion() < SKSE::RUNTIME_SSE_1_6_629) { /* 返回 false */ }
    return true;
}
```

- 门槛示例：CorpseESP 用 `RUNTIME_SSE_1_6_629`（AE）；FollowerSummonAllyFix 用
  `RUNTIME_SSE_1_5_39`（更宽容）。按插件实际需求选择。

## 5. 加载流程（SKSEPlugin_Load）

```cpp
extern "C" DLLEXPORT bool SKSEAPI SKSEPlugin_Load(SKSE::LoadInterface const* a_skse)
{
    REL::Module::reset();          // Clib-NG bug workaround（两个源项目都在做）
    initialize_log();
    SKSE::Init(a_skse);
    SKSE::AllocTrampoline(1 << 4); // 需要跳板时

    SKSE::GetMessagingInterface()->RegisterListener(message_handler);
    // 按功能：Config::load(); Hooks::install(); HitEvents::install();
    return true;
}
```

## 6. 生命周期消息

`SKSE::MessagingInterface` 在 `kDataLoaded` 后做数据加载完的初始化：

- `kDataLoaded`：所有插件已加载、数据就绪（阵营查找、Present 钩子、MCP 面板注册等）。
- `kNewGame` / `kPostLoadGame`：新档/读档后重新处理存量对象。
- `kPreLoadGame` / `kSaveGame` / `kDeleteGame` 按需。

## 7. VR 特有注意

- VR 构建依赖 CommonLibSSE 的 `extern/openvr` 子模块；缺失时报错。
  初始化：`git submodule update --init extern/CommonLibSSE` 后再
  `git -C extern/CommonLibSSE submodule update --init extern/openvr`。
- 多运行时下 VR 独有的虚函数/基类差异按 `SKYRIM_CROSS_VR` 处理（见
  `small-project-cpp-rules` 无关，此处仅提约束：保持 vtable 槽位对齐）。

## 8. 铁律

- 不在插件源码中硬编码 SE-only 或 AE-only 的原始地址/偏移；一律走地址库。
- 新增"调用某引擎函数"前先查 CommonLibSSE 是否已有封装（`RE::`/`REL::`/`SKSE::`）。
- 涉及虚表替换时注意 slot 跨运行时一致性，并优先选用其他 mod 已验证的 slot
  （如 `Character::Update` 的 `0xAD` 与 TDM 一致）。
