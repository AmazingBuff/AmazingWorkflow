# Check the runtime only when engine integration is involved

The default CMake provides SE/AE/VR switches, and the examples enable SE/AE.
These switches and the export metadata are not cross-runtime verification
results. Determine the actual versions the current plugin supports first, then
check the selected CommonLib, SKSE, Address Library, and related layouts
against the target runtime.

For new engine calls, prefer CommonLib's existing interfaces. A relocatable
table address does not mean the vtable slot and calling convention are the
same across versions; do not treat the reference project's slots, offsets, or
comments as evidence for another target version's branch.

Choose message timing per module's actual needs. Register a message listener
only when game data is required; if both a new game and a load should take
effect, cover both paths; handle repeated registration of listeners and hooks
according to the actual lifecycle. The reference handling only one message
does not mean the target project must also omit the others. When no related
module exists, do not generate an empty message_handler.

Determine responsibility separately for configuration sharing, event sink
lifecycle, game object references, the render thread, device change, and COM
resources. Do not substitute "consistent with the reference implementation"
for review, and do not implement a whole mechanism in advance for potential
future features.

The minimal template keeps the reference's entry/metadata shape; after adding
concrete features, re-check declarations such as UsesNoStructs and
version-specific workarounds such as REL::Module::reset against the selected
dependency branch, its maintenance status, license, and implementation
differences. A successful compile only proves the build; actual callbacks,
hooks, and game behavior still need verification on each runtime you claim to
support.
