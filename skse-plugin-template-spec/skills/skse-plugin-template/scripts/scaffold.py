#!/usr/bin/env python3
"""SKSE plugin scaffold.

Generates a new Skyrim SKSE plugin project (multi-runtime SE/AE/VR via CommonLibSSE)
from the skse-plugin-template skill's templates/.

Usage:
    python scaffold.py --name MyPlugin --author "Your Name" --dir E:/SkyrimTools/Proj/MyPlugin
    python scaffold.py --help
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = SKILL_DIR / "templates"
FEATURES_DIR = TEMPLATE_DIR / "features"

# 与两个源项目（CorpseESP / FollowerSummonAllyFix）一致的 vcpkg builtin-baseline
DEFAULT_VCPKG_BASELINE = "cd61e1e26a038e82d6550a3ebbe0fbbfe7da78e3"

RUNTIMES = {
    "all": {"SE": "ON", "AE": "ON", "VR": "ON"},
    "se": {"SE": "ON", "AE": "OFF", "VR": "OFF"},
    "ae": {"SE": "OFF", "AE": "ON", "VR": "OFF"},
    "vr": {"SE": "OFF", "AE": "OFF", "VR": "ON"},
    "se-ae": {"SE": "ON", "AE": "ON", "VR": "OFF"},
    "se-vr": {"SE": "ON", "AE": "OFF", "VR": "ON"},
    "ae-vr": {"SE": "OFF", "AE": "ON", "VR": "ON"},
}

# 功能模块描述：文件、vcpkg 依赖、CMake find_package / 链接、main.cpp 生命周期接线
FEATURES = {
    "config": {
        "files": ["src/config.h", "src/config.cpp"],
        "vcpkg_deps": ["simpleini"],
        "cmake_find": ["simpleini CONFIG REQUIRED"],
        "link": ["SimpleIni::SimpleIni"],
        "includes": ['#include "config.h"'],
        "load_glue": ["Config::load();"],
        "dataloaded_glue": [],
    },
    "hotkey": {
        "files": ["src/input.h", "src/input.cpp"],
        "depends": ["config"],
        "vcpkg_deps": [],
        "cmake_find": [],
        "link": [],
        "includes": ['#include "input.h"'],
        "load_glue": [],
        "dataloaded_glue": [],
    },
    "present_hook": {
        "files": ["src/esp_renderer.h", "src/esp_renderer.cpp"],
        "vcpkg_deps": [],
        "cmake_find": ["directxtk CONFIG REQUIRED"],
        "link": ["Microsoft::DirectXTK", "d3d11", "dxgi"],
        "includes": ['#include "esp_renderer.h"'],
        "load_glue": [],
        "dataloaded_glue": ["ESPRenderer::install();"],
    },
    "vtable_hook": {
        "files": ["src/hooks.h", "src/hooks.cpp"],
        "vcpkg_deps": [],
        "cmake_find": [],
        "link": [],
        "includes": ['#include "hooks.h"'],
        "load_glue": ["Hooks::install();"],
        "dataloaded_glue": [],
    },
    "event_sink": {
        "files": ["src/hit_events.h", "src/hit_events.cpp"],
        "vcpkg_deps": [],
        "cmake_find": [],
        "link": [],
        "includes": ['#include "hit_events.h"'],
        "load_glue": ["HitEvents::install();"],
        "dataloaded_glue": [],
    },
}

COMMONLIB_URLS = {
    "ng": "https://github.com/alandtse/CommonLibSSE-NG.git",
    "vr": "https://github.com/alandtse/CommonLibVR.git",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def fail(msg: str) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def parse_version(version: str) -> tuple[str, str, str]:
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)$", version)
    if not m:
        fail(f"version must look like 1.0.0, got: {version!r}")
    return m.group(1), m.group(2), m.group(3)


def substitute(text: str, values: dict[str, str], ignore: frozenset[str] = frozenset()) -> str:
    """Replace {{KEY}} placeholders; fail loudly on any leftover placeholder.

    `ignore` holds keys that are substituted later by subst_in_place() (line-level
    placeholders whose replacement must preserve the placeholder line's indent).
    """
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    leftovers = [p for p in re.findall(r"\{\{[A-Za-z_][A-Za-z0-9_]*\}\}", text) if p[2:-2] not in ignore]
    if leftovers:
        fail(f"unsubstituted template placeholders: {sorted(set(leftovers))}")
    return text


def write_newline(path: Path, content: str) -> None:
    """Write with CRLF (like the source projects)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\r\n") as f:
        f.write(content)


def build_src_cmake_lists(features: list[str]) -> str:
    source_files = ["${SOURCE_DIR}/main.cpp"]
    header_files = ["${SOURCE_DIR}/pch.h"]
    cmake_find: list[str] = []
    link_libs: list[str] = ["spdlog::spdlog", "fmt::fmt", "CommonLibSSE::CommonLibSSE"]

    for feat in features:
        for f in FEATURES[feat]["files"]:
            if f.endswith(".cpp"):
                source_files.append(f"${{SOURCE_DIR}}/{f.split('/', 1)[1]}")
            else:
                header_files.append(f"${{SOURCE_DIR}}/{f.split('/', 1)[1]}")
        cmake_find.extend(FEATURES[feat]["cmake_find"])
        link_libs.extend(FEATURES[feat]["link"])

    def lines(items: list[str], indent: str = "    ") -> str:
        return "\n".join(indent + i for i in items)

    return f"""set(ROOT_DIR "${{CMAKE_CURRENT_SOURCE_DIR}}/..")
set(SOURCE_DIR "${{ROOT_DIR}}/src")

# 小型稳定目标：显式列出 sources，避免 GLOB 在新增文件后静默过期
set(SOURCE_FILES
{lines(source_files)}
)
set(HEADER_FILES
{lines(header_files)}
)

set(VERSION_HEADER "${{CMAKE_CURRENT_BINARY_DIR}}/src/Plugin.h")
string(TIMESTAMP PLUGIN_BUILD_DATE "%Y/%m/%d")
configure_file(
    "${{ROOT_DIR}}/cmake/Plugin.h.in"
    "${{VERSION_HEADER}}"
    @ONLY
)

configure_file(
    "${{ROOT_DIR}}/cmake/version.rc.in"
    "${{CMAKE_CURRENT_BINARY_DIR}}/version.rc"
    @ONLY
)

source_group("Source" FILES ${{SOURCE_FILES}})
source_group("Header" FILES ${{HEADER_FILES}} ${{VERSION_HEADER}})

add_library(
    ${{PROJECT_NAME}}
    SHARED
    ${{HEADER_FILES}}
    ${{SOURCE_FILES}}
    ${{VERSION_HEADER}}
    ${{CMAKE_CURRENT_BINARY_DIR}}/version.rc
)

target_compile_features(
    ${{PROJECT_NAME}}
    PRIVATE
    cxx_std_23
)

# Align the MSVC toolset with the one vcpkg uses for dependencies (spdlog).
# CMake 3.31 drops the `version=` clause from CMAKE_GENERATOR_TOOLSET and writes
# a plain `v143`, which resolves to an older toolset (14.38) whose STL lacks the
# vectorized symbols 14.44 objects reference, causing LNK2019 at link time.
set_target_properties(
    ${{PROJECT_NAME}}
    PROPERTIES
    VS_GLOBAL_VCToolsVersion "14.44.35207"
)

if("${{CMAKE_CXX_COMPILER_ID}}" STREQUAL "MSVC")
    target_compile_options(
        ${{PROJECT_NAME}}
        PRIVATE
        "/sdl"
        "/utf-8"
        "/Zi"
        "/permissive-"
        "/Zc:preprocessor"
        "/wd4200"
        "$<$<CONFIG:DEBUG>:/ZI>"
        "$<$<CONFIG:RELEASE>:/Zi;/Zc:inline;/JMC-;/Ob3>"
    )

    target_compile_definitions(
        ${{PROJECT_NAME}}
        PRIVATE
        NOMINMAX
    )

    target_link_options(
        ${{PROJECT_NAME}}
        PRIVATE
        "$<$<CONFIG:DEBUG>:/INCREMENTAL;/OPT:NOREF;/OPT:NOICF>"
        "$<$<CONFIG:RELEASE>:/INCREMENTAL:NO;/OPT:REF;/OPT:ICF;/DEBUG:FULL>"
    )
endif()

target_include_directories(
    ${{PROJECT_NAME}}
    PRIVATE
    ${{CMAKE_CURRENT_BINARY_DIR}}/src
    ${{SOURCE_DIR}}
)

# dependency macros
macro(find_dependency_path DEPENDENCY FILE)
    if(NOT ${{DEPENDENCY}} STREQUAL "")
        message(STATUS "Searching for ${{DEPENDENCY}} using file ${{FILE}}")
        find_path(PATH
            ${{FILE}}
            PATHS
            "../extern/${{DEPENDENCY}}"
            "extern/${{DEPENDENCY}}"
            "../external/${{DEPENDENCY}}"
            "external/${{DEPENDENCY}}")
        set("${{DEPENDENCY}}Path" "${{PATH}}")
        if("${{${{DEPENDENCY}}Path}}" STREQUAL "PATH-NOTFOUND")
            message(STATUS "Getting environment variable for ${{DEPENDENCY}}Path: $ENV{{${{DEPENDENCY}}Path}}")
            set("${{DEPENDENCY}}Path" "$ENV{{${{DEPENDENCY}}Path}}")
        endif()
        if (NOT "${{${{DEPENDENCY}}Path}}" STREQUAL "")
            message(STATUS "Found ${{DEPENDENCY}} in ${{${{DEPENDENCY}}Path}}; adding")
            add_subdirectory("${{${{DEPENDENCY}}Path}}" ${{DEPENDENCY}})
        endif()
    endif()
endmacro()

# dependencies
find_dependency_path(CommonLibSSE include/REL/Relocation.h)

if(("${{CommonLibSSEPath}}" STREQUAL "CommonLibSSEPath-NOTFOUND") OR "${{CommonLibSSEPath}}" STREQUAL "")
    # fallback to CommonLibSSEPath_NG from environment
    message(STATUS "Found CommonLibSSE from CommonLibSSEPath_NG environment variable")
    add_subdirectory("$ENV{{CommonLibSSEPath_NG}}" CommonLibSSE EXCLUDE_FROM_ALL)
endif()

# CommonLibSSE 由本仓库源码构建时，SKSE_SUPPORT_PATCH_SAFETY=OFF 下
# Trampoline.cpp 有无用形参（C4100），与全局 /WX 冲突。在项目侧静默该警告，
# 保持三方库源码原样（不改 extern/CommonLibSSE）。
if(TARGET CommonLibSSE AND MSVC)
    target_compile_options(CommonLibSSE PRIVATE /wd4100)
endif()

find_package(spdlog CONFIG REQUIRED)
find_package(fmt CONFIG REQUIRED)
{'' if not cmake_find else '\n'.join('find_package(' + c + ')' for c in cmake_find)}

target_link_libraries(
    ${{PROJECT_NAME}}
    PRIVATE
{lines(link_libs)}
)

target_precompile_headers(
    ${{PROJECT_NAME}}
    PRIVATE
    ${{SOURCE_DIR}}/pch.h
)

install(
    FILES
        "$<TARGET_FILE:${{PROJECT_NAME}}>"
    DESTINATION "SKSE/Plugins"
    COMPONENT "main"
)

install(
    FILES
        "$<TARGET_PDB_FILE:${{PROJECT_NAME}}>"
    DESTINATION "/"
    COMPONENT "pdbs"
)

if("${{COPY_OUTPUT}}")
    add_custom_command(
        TARGET
        "${{PROJECT_NAME}}"
        POST_BUILD
        COMMAND
        "${{CMAKE_COMMAND}}" -E copy_if_different "$<TARGET_FILE:${{PROJECT_NAME}}>" "${{CompiledPluginsPath}}/SKSE/Plugins/"
        COMMAND
        "${{CMAKE_COMMAND}}" -E copy_if_different "$<TARGET_PDB_FILE:${{PROJECT_NAME}}>" "${{CompiledPluginsPath}}/SKSE/Plugins/"
        VERBATIM
    )
endif()
"""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a new Skyrim SKSE plugin (multi-runtime SE/AE/VR via CommonLibSSE).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Available --features (comma separated): " + ", ".join(FEATURES) + "\n"
            "Available --runtimes: " + ", ".join(RUNTIMES)
        ),
    )
    parser.add_argument("--name", required=True, help="plugin/project name (DLL, CMake project, log name)")
    parser.add_argument("--author", default="Your Name", help="author shown in SKSEPlugin_Version")
    parser.add_argument("--description", default="A Skyrim SKSE plugin.", help="one-line description")
    parser.add_argument("--version", default="1.0.0", help="version like 1.0.0")
    parser.add_argument("--runtimes", default="all", choices=sorted(RUNTIMES), help="runtime set to compile in")
    parser.add_argument(
        "--features",
        default="",
        help="comma separated feature modules, e.g. config,hotkey,present_hook,vtable_hook,event_sink",
    )
    parser.add_argument("--commonlib", default="ng", choices=sorted(COMMONLIB_URLS), help="CommonLibSSE variant")
    parser.add_argument("--baseline", default=DEFAULT_VCPKG_BASELINE, help="vcpkg builtin-baseline")
    parser.add_argument("--dir", default=None, help="output directory (default: ./<name>)")
    parser.add_argument("--git-init", action="store_true", help="run `git init` in the generated project")
    args = parser.parse_args()

    if not re.match(r"^[A-Za-z][A-Za-z0-9_]*$", args.name):
        fail("name must match ^[A-Za-z][A-Za-z0-9_]*$")

    features = [f.strip() for f in args.features.split(",") if f.strip()]
    unknown = [f for f in features if f not in FEATURES]
    if unknown:
        fail(f"unknown features: {unknown}; available: {', '.join(FEATURES)}")
    # 依赖检查：hotkey 需要 config
    if "hotkey" in features and "config" not in features:
        fail("feature 'hotkey' requires feature 'config' (add --features config,hotkey)")
    # present_hook + hotkey：热键在 on_present 中轮询
    present_plus_hotkey = "present_hook" in features and "hotkey" in features

    out_dir = Path(args.dir) if args.dir else Path.cwd() / args.name
    if out_dir.exists() and any(out_dir.iterdir()):
        fail(f"output directory not empty: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)

    maj, minor, patch = parse_version(args.version)
    name_lower = args.name.lower()

    # 预计算功能相关片段
    vcpkg_extra = ""
    all_vcpkg_deps: list[str] = []
    for feat in features:
        for dep in FEATURES[feat]["vcpkg_deps"]:
            if dep not in all_vcpkg_deps:
                all_vcpkg_deps.append(dep)
    if all_vcpkg_deps:
        vcpkg_extra = ",\n    " + ",\n    ".join('"%s"' % d for d in all_vcpkg_deps)

    # main.cpp 依赖 PCH 强制注入（target_precompile_headers），这里只追加功能模块头
    includes: list[str] = []
    for feat in features:
        includes.extend(FEATURES[feat]["includes"])
    load_glue: list[str] = []
    dataloaded_glue: list[str] = []
    for feat in features:
        load_glue.extend(FEATURES[feat]["load_glue"])
        dataloaded_glue.extend(FEATURES[feat]["dataloaded_glue"])

    renderer_extra_includes = ['#include "input.h"'] if present_plus_hotkey else []
    on_present_body = ["Input::poll();"] if present_plus_hotkey else []

    commonlib_url = COMMONLIB_URLS[args.commonlib]
    commonlib_branch = "ng"

    def read_template(rel: str) -> str:
        return (TEMPLATE_DIR / rel).read_text(encoding="utf-8")

    def subst_in_place(content: str, line_indent_placeholders: dict[str, list[str]]) -> str:
        """Replace whole placeholder lines, preserving the placeholder line's leading indent."""
        result = []
        for line in content.splitlines(keepends=True):
            stripped = line.strip()
            ph = next((p for p in line_indent_placeholders if stripped == "{{" + p + "}}"), None)
            if ph is None:
                result.append(line)
                continue
            indent = line[: len(line) - len(line.lstrip())]
            glue = line_indent_placeholders[ph]
            block = "\n".join(indent + g for g in glue) if glue else ""
            result.append(block + ("\n" if line.endswith("\n") else ""))
        return "".join(result)

    # 通用 {{KEY}} 替换
    values = {
        "PROJECT_NAME": args.name,
        "PROJECT_NAME_LOWER": name_lower,
        "PROJECT_VERSION": args.version,
        "PROJECT_VERSION_MAJOR": maj,
        "PROJECT_VERSION_MINOR": minor,
        "PROJECT_VERSION_PATCH": patch,
        "AUTHOR": args.author,
        "DESCRIPTION": args.description,
        "COMMONLIB_URL": commonlib_url,
        "COMMONLIB_BRANCH": commonlib_branch,
        "ENABLE_SKYRIM_SE": RUNTIMES[args.runtimes]["SE"],
        "ENABLE_SKYRIM_AE": RUNTIMES[args.runtimes]["AE"],
        "ENABLE_SKYRIM_VR": RUNTIMES[args.runtimes]["VR"],
        "VCPKG_BASELINE": args.baseline,
        "VCPKG_EXTRA_DEPS": vcpkg_extra,
        "DATE": date.today().strftime("%Y/%m/%d"),
    }

    # 行级占位符（保持缩进）
    line_placeholders: dict[str, list[str]] = {
        "FEATURE_INCLUDES": includes,
        "ON_LOAD": load_glue,
        "ON_DATALOADED": dataloaded_glue,
        "RENDERER_EXTRA_INCLUDES": renderer_extra_includes,
        "ON_PRESENT_BODY": on_present_body,
    }

    # 顶层核心模板（templates/*）
    core_files = [
        "CMakeLists.txt",
        "CMakePresets.json",
        "vcpkg.json",
        "README.md",
        ".gitignore",
        ".gitmodules",
    ]
    for rel in core_files:
        content = substitute(read_template(rel), values)
        write_newline(out_dir / rel, content)

    # cmake/
    for rel in ["packaging.cmake", "Plugin.h.in", "version.rc.in"]:
        content = substitute(read_template(f"cmake/{rel}"), values)
        write_newline(out_dir / "cmake" / rel, content)

    # src/main.cpp 与 pch.h（含行级占位符）
    for rel, ph in [("src/main.cpp", line_placeholders), ("src/pch.h", {})]:
        content = substitute(read_template(rel), values, ignore=frozenset(line_placeholders))
        if ph:
            content = subst_in_place(content, {k: v for k, v in ph.items() if v is not None})
        write_newline(out_dir / rel, content)

    # 功能模块
    for feat in features:
        for rel in FEATURES[feat]["files"]:
            src = FEATURES_DIR / feat / rel
            content = substitute(
                src.read_text(encoding="utf-8"),
                values,
                ignore=frozenset({"RENDERER_EXTRA_INCLUDES", "ON_PRESENT_BODY"}),
            )
            if rel.endswith("esp_renderer.cpp"):
                content = subst_in_place(
                    content,
                    {
                        "RENDERER_EXTRA_INCLUDES": renderer_extra_includes,
                        "ON_PRESENT_BODY": on_present_body,
                    },
                )
            write_newline(out_dir / rel, content)

    # 生成 src/CMakeLists.txt
    write_newline(out_dir / "src" / "CMakeLists.txt", build_src_cmake_lists(features))

    # git init（可选）
    if args.git_init:
        subprocess.run(["git", "init", str(out_dir)], check=False)

    # 汇总
    print(f"Scaffolded SKSE plugin at: {out_dir}")
    print(f"  name:      {args.name}")
    print(f"  author:    {args.author}")
    print(f"  version:   {args.version}")
    print(f"  runtimes:  {args.runtimes} (SE={RUNTIMES[args.runtimes]['SE']}, AE={RUNTIMES[args.runtimes]['AE']}, VR={RUNTIMES[args.runtimes]['VR']})")
    print(f"  commonlib: {commonlib_url}")
    print(f"  features:  {', '.join(features) if features else '(none)'}")
    print()
    print("Next steps:")
    print(f"  cd {out_dir}")
    print("  git submodule update --init --recursive")
    print('  cmake --preset "msvc release"')
    print('  cmake --build --preset "msvc release"')


if __name__ == "__main__":
    main()
