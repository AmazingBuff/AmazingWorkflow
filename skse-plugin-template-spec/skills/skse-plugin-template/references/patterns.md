# First-party implementation patterns

The authoritative sources are under `templates/`. These notes explain the
invariants that must remain true when extending them.

## Entry point and metadata

`main.cpp` owns logging, the SKSE Load entry point, and lifecycle dispatch.
Plugin Query/version metadata is not first-party C++: generated
`src/CMakeLists.txt` calls `add_commonlibsse_plugin(...)` with `AUTHOR` and
`USE_ADDRESS_LIBRARY`, allowing CommonLibSSE-NG to emit metadata consistent
with the selected SE/AE/VR options.

Do not add a fixed AE minimum or `RUNTIME_SSE_LATEST` list. Check the result of
message-listener registration and return failure instead of reporting a
successful load.

## Configuration

`Config::load()` reads SimpleIni values, updates the atomic enabled flag, and
writes a complete default file when needed. Settings are owned by one static
value; `get()` borrows read-only state and `get_mutable()` is for game-thread
changes. Add parsing helpers only when a generated field actually calls them.
Unused example helpers are forbidden under `/W4 /WX`.

## Hotkey frame source

`Input::poll()` reads `Config::get().hotkey` and performs edge-triggered
`GetAsyncKeyState` polling. It is only generated when both `config` and
`present_hook` are selected. The generator injects exactly one reachable call
at the start of the Present callback:

```cpp
void on_present_inner(IDXGISwapChain* a_swap_chain)
{
    Input::poll();
    record_and_execute(a_swap_chain);
}
```

Do not advertise the hotkey without a frame source. Any alternative source
would be a public feature/dependency change and must update validation, tests,
and docs together.

## Present rendering

Persistent state is limited to device-bound helpers:

- one retained D3D11 device used to detect device changes;
- one deferred context;
- DirectXTK CommonStates, BasicEffect, and PrimitiveBatch bound to that device.

On device change, reset all five resources before recreating them. Every frame
uses local `ComPtr` values for the back buffer, render-target view, command
list, and immediate context. Record all plugin state and draws on the deferred
context, call `FinishCommandList`, then `ClearState` so the deferred context
releases resource references. Execute with:

```cpp
immediate_context->ExecuteCommandList(command_list.Get(), TRUE);
```

The `TRUE` restore flag isolates the entire immediate-context pipeline, not
only OM/RS state. Return from the drawing function before calling the original
Present so every per-frame COM reference and command list has been released.
Never retain a swap-chain back buffer or RTV globally.

## Vtable hook

Resolve the Character vtable through `RE::VTABLE_Character[0]` and
`REL::Relocation`. The example slot is a named local static constant. Keep the
original function pointer and call it from the hook. Do not hard-code a raw
runtime address.

## Event sink

The event source does not own sink memory. Use the authoritative static object:

```cpp
namespace
{

class HitSink final : public RE::BSTEventSink<RE::TESHitEvent>
{
public:
    RE::BSEventNotifyControl ProcessEvent(
        RE::TESHitEvent const*,
        RE::BSTEventSource<RE::TESHitEvent>*
    ) override;
};

HitSink g_sink;

}
```

Do not replace it with a bare allocation. Omit parameter names until the event
or source is used, so generated first-party code remains warning-clean.

## Error boundaries

Input/template/Git failures are Python-side checked errors. CMake fails with an
actionable CommonLib acquisition command. C++ Load failures return `false`.
Present catches exceptions before crossing the IDXGI callback boundary and
always delegates to the original Present function.
