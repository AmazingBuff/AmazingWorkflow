# Reusable code: select, trim, wire in

## Before selecting

First write down "what problem this feature needs it to solve". Do not add
tools, managers, state classes, or submodules without a consumer. Read the
candidate implementation and its callers, and distinguish:

- Generic mechanisms: e.g. message listening, input event translation, COM
  state management.
- Plugin conventions: e.g. namespaces, log aliases, paths, field naming.
- Original business coupling: e.g. corpse collection, outline pass, filter
  fields, QuickLoot notifications.
- Lifecycle and implicit preconditions: which thread calls it, when objects
  exist, who releases references, whether duplicate registration is allowed.

Decide whether to reuse directly, extract a small piece, or reimplement for
the current need only after these four categories are separated.

## Common adaptations

### Configuration

The Config + Setting responsibility arrangement can serve as a reference.
Keep only the fields, defaults, validation, and serialization the current
plugin needs. Do not copy corpse distance, scan period, display mode, or a
hotkey with no current input feature. Whether get_config returns a reference
or a snapshot depends on the actual calling thread and mutation style; do not
keep a data race for the sake of literal consistency. Configuration interface
changes must update all consumers together. Functions doing file I/O or
allocation should not blindly keep noexcept.

### Input

When only responding to game events, reuse the BSInputDeviceManager /
BSTEventSink wiring approach. Determine whether the configuration stores VK
codes, scan codes, or game macro key codes before keeping the necessary
translation. Register event sources according to the game lifecycle, handling
duplicate registration, menu/text input, and the devices the user needs.
Delete Menu, PulseTimer, or configuration dependencies that have no
corresponding feature in the source. Input does not require a Present hook,
let alone pulling in the rendering system along with it.

### Rendering utilities

Only when the feature really draws, select the needed parts among
PresentHook, CommonStates, D3D11StateCapture, and ShaderManager. Judge
Color/projection/hash/timer independently; "they are all generic utilities" is
not a reason to copy the whole package. When using state capture, check every
slot the current pass changes and the restore scope; a generic name does not
mean it covers all states. After removing the original passes, shader
members, and business inputs, update construction/destruction,
creation/release paths, and CMake dependencies together. Do not leave an empty
draw or consumer-less shader pairs to prove "structural completeness".

### Menu

Introduce SKSE-MCP only when the user needs a UI and chooses MCP. The
registration flow and settings callbacks can be reused; replace the product
title, control fields, and save action. Do not keep an interaction that only
changes button text without actual rebind handling and claim it is
implemented. Without a menu feature, input and configuration should not
depend on Menu either.

## Definition of done

For every reuse, state: source location, responsibilities kept, coupling
removed, interface/lifecycle adjustments, and actual verification. Ensure
includes, CMake dependencies, entry initialization, and runtime cleanup all
correspond to the trimmed implementation. Literal identity is unnecessary;
necessary fixes can land directly in the target project without requiring the
reference project to change first. Preserve the original source's
copyright/license information, and avoid filling the original author's
identity in as the new project's author.
