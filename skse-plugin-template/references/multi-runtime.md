# Runtime and rendering constraints

SE/AE is the reference default. CLI selections se, ae, se-ae, vr, all, se-vr,
ae-vr map to the corresponding ENABLE_SKYRIM_* options before CommonLib is
added. VR requires initialized nested OpenVR content and matching SKSE and
Address Library. The reference does not establish VR behavior for its renderer.
Both the generator and CMake reject VR for present_hook/vtable_hook until a
verified VR implementation replaces these examples.

main.cpp defines metadata explicitly, using PluginVersionData, UsesAddressLibrary
and UsesNoStructs like the reference. These are declarations to review for each
actual plugin, not proof of struct/runtime independence. Query rejects null
arguments and editor mode but does not certify a runtime matrix. Do not infer
universal AE compatibility from metadata or a successful build.

Engine addresses use CommonLib relocations and runtime-aware accessors. A table
relocation does not prove a virtual slot: the optional Character Update example
uses the flat header's 0xAD slot and void(Actor*, float); verify the executable
ABI before enabling it in a release. Do not invent IDs or transplant slots to VR.

## Lifecycle and input

Load initializes logging/SKSE and Setting, retaining the source project's
REL::Module::reset workaround pending review on dependency upgrades. DataLoaded
installs optional event/vtable modules. NewGame and PostLoadGame install renderer
and input; SaveGame persists settings. Renderer/input installation is idempotent.
If the renderer is still absent on a game-ready message, it can retry on the
next such message; this skeleton does not add an asynchronous retry loop.

Config stores Windows virtual-key codes. InputManager converts with
MapVirtualKeyA(..., MAPVK_VK_TO_VSC), compares keyboard ButtonEvent codes and
acts only on IsDown. Extra UI/text input, extended keys, mouse, gamepad and VR
controller support require project-specific work. Do not claim they are covered
by the default keyboard binding. Static event sinks have process lifetime.

## Renderer pattern

Renderer is the public facade. A private OverlayDirector owns rendering state
and serialization. PresentHook is a singleton with its callback and original
Present function as members. It patches COM slot 8 from the real swap chain
using REL::Relocation::write_vfunc, publishes callback/original before patching,
guards repeat installation, skips DXGI_PRESENT_TEST and preserves original
Present after the callback even if plugin C++ code throws.

Use REX::W32 types end-to-end as in the reference. The generated renderer obtains
the actual device/context and calls a draw extension point; it does not create
DirectXTK effects, change pipeline state, retain back buffers or draw gameplay
objects by default. New passes should follow the reference's dx11 helpers:

1. Construct D3D11StateCapture with a valid context and call capture once.
2. Set only the pipeline slots your pass needs; submit its rendering.
3. Call restore on every exit, including exceptions, before the capture object
   releases its saved COM references. The helper destructor releases references;
   it does not automatically restore state.

The reused helper captures a specific subset (one RTV, selected IA/VS/PS slots,
blend/depth/rasterizer, viewport/scissor). It is not a universal D3D11 state
snapshot. Extend it if new passes touch other slots or GS/HS/DS/UAV state, and
check class-instance array capacity when changing shader use. Do not call
capture twice on one instance without releasing the previous references.

compile_shader returns an owned blob; release it and created device resources
at their lifecycle boundaries. Avoid retained swap-chain textures/views without
a complete resize strategy. Microsoft's [ResizeBuffers contract](https://learn.microsoft.com/en-us/windows/win32/api/dxgi/nf-dxgi-idxgiswapchain-resizebuffers)
requires direct and indirect back-buffer references to be released before resize.
Hook/device replacement, interaction with other overlays and actual render-thread
ownership still need live-game tests; the skeleton is not hot-unload support.
