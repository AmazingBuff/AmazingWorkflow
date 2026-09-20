# How to read the reference project

Reference project: Highlight-Lootable-Corpses. Its purpose is to provide an
existing organizational pattern and concrete implementation cases, not a
module checklist for the target project, an unmodifiable specification, or a
file-by-file sync source.

| Problem to solve | Reading entry | What to extract |
| --- | --- | --- |
| How the project and metadata are organized | Root CMakeLists, CMakePresets, cmake/plugin.h.in, main.cpp, pch.h | Build order, generated-file locations, entry and namespace conventions. |
| How INI separates responsibilities | src/config/ and its callers | The config module's interface and read/write flow, not the original fields in full. |
| How input reaches the game | src/input/ | Event subscription and code-value translation; keep devices and trigger behavior per need. |
| How a menu connects to settings | src/ui/ui_menu.* and extern/SKSE-MCP | Reference if and only if that UI approach is needed. |
| How graphics code is split | src/render/, dx11/, shader_manager.*, cmake/embed_shaders.cmake | Choose layering, state utilities, and the generation flow by actual rendering scale. |
| Whether a utility is reusable | base/def.h, render_util.*, pulse_timer.* | Check consumers and dependencies item by item; pick functions/classes with a purpose. |

Do not introduce search, filtering, QuickLoot, outline/icon passes, or the
"generic" modules above by default. They enter the target project only when
they solve a concrete need of the target project.

The old skill constraints of "fixed universal skeleton", "22 files must be
identical", and "hash equality equals done" have been removed;
check_reference.py, reference_model.py, and reference.json no longer belong to
this skill. The maintenance standard is now: whether the current feature has a
reasonable file layout, whether CMake configures only what is actually needed,
and whether reused code has completed dependency trimming and adaptation.
