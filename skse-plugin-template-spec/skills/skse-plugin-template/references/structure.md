# SKSE 插件工程结构

> 提取自 CorpseESP 与 FollowerSummonAllyFix 两个真实项目；两者结构高度一致，
> 差异只在功能模块（CorpseESP 多渲染/配置，FollowerSummonAllyFix 多钩子/事件）。

## 完整目录树

```text
<Project>/
├── .gitignore                 # /build、IDE、CMake、编译产物、日志
├── .gitmodules                # extern/CommonLibSSE 子模块
├── CMakeLists.txt             # 根：project() + 选项 + add_subdirectory(src) + packaging
├── CMakePresets.json          # 受支持工作流预设（VS2022 + vcpkg + static-md + 14.44 工具集）
├── CMakeUserPresets.json      # 本机专用（含个人路径），被 .gitignore 排除，不提交
├── README.md                  # 安装/构建/配置说明
├── vcpkg.json                 # 依赖清单（manifest 模式）
├── cmake/
│   ├── packaging.cmake        # CPack ZIP + component install
│   ├── Plugin.h.in            # 由 project() 生成 Plugin::VERSION / Plugin::NAME
│   └── version.rc.in          # Windows VERSIONINFO 资源
├── extern/
│   └── CommonLibSSE/          # git submodule（引擎库，官方仍以 submodule 消费）
├── docs/                      # 按需；复杂功能带 DESIGN.md（如 FollowerSummonAllyFix）
└── src/
    ├── CMakeLists.txt         # SHARED 目标定义（见下）
    ├── pch.h                  # 预编译头
    ├── main.cpp               # SKSE 插件入口
    └── <feature>.*            # 功能模块（config/input/esp_renderer/hooks/hit_events...）
```

## 根 CMakeLists.txt（多运行时开关）

职责：`project()`、用户选项（运行时开关、COPY_OUTPUT）、依赖与子目录装配、打包。
两个源项目的一致性要点：

```cmake
cmake_minimum_required(VERSION 3.22)

project(<Name> VERSION <version> LANGUAGES CXX)

# 运行时开关（多运行时关键）：默认全开 → 单 DLL 支持 SE/AE/VR
option(ENABLE_SKYRIM_SE "Enable support for Skyrim SE" ON)
option(ENABLE_SKYRIM_AE "Enable support for Skyrim AE" ON)
option(ENABLE_SKYRIM_VR "Enable support for Skyrim VR" OFF)
# CommonLibSSE 自带测试默认 ON；插件作为消费方默认关闭（先于 add_subdirectory 定义，选项继承）
option(BUILD_TESTS "Enable CommonLibSSE unit tests" OFF)

option(COPY_OUTPUT "Copy build output to the game directory" OFF)
# 需设置 CompiledPluginsPath 环境变量

list(APPEND CMAKE_MODULE_PATH "${PROJECT_SOURCE_DIR}/cmake")
add_subdirectory(src)
include(cmake/packaging.cmake)
```

> `BUILD_TESTS` 必须在 `add_subdirectory(src)`（进而 CommonLibSSE）之前定义，让
> CommonLibSSE 的 `option()` 继承到 OFF。

## src/CMakeLists.txt（SHARED 目标）

职责：定义插件目标、编译旗标、依赖、PCH、安装。要点（两项目一致）：

```cmake
set(ROOT_DIR "${CMAKE_CURRENT_SOURCE_DIR}/..")
set(SOURCE_DIR "${ROOT_DIR}/src")

# 显式列出 sources（避免 GLOB 在新增文件后静默过期）
set(SOURCE_FILES ${SOURCE_DIR}/main.cpp ...)
set(HEADER_FILES ${SOURCE_DIR}/pch.h ...)

configure_file("${ROOT_DIR}/cmake/Plugin.h.in"  .../Plugin.h  @ONLY)
configure_file("${ROOT_DIR}/cmake/version.rc.in" .../version.rc @ONLY)

add_library(${PROJECT_NAME} SHARED ${HEADER_FILES} ${SOURCE_FILES} ${VERSION_HEADER} .../version.rc ...)
target_compile_features(${PROJECT_NAME} PRIVATE cxx_std_23)

# 关键：与 vcpkg 依赖（spdlog）对齐 MSVC 工具集，避免 LNK2019
set_target_properties(${PROJECT_NAME} PROPERTIES VS_GLOBAL_VCToolsVersion "14.44.35207")

# MSVC：/sdl /utf-8 /Zi /permissive- /Zc:preprocessor、NOMINMAX、Debug/Release 链接选项

# CommonLibSSE：优先 extern/ 下 submodule，否则回退环境变量
find_dependency_path(CommonLibSSE include/REL/Relocation.h)   # add_subdirectory
if(CommonLibSSEPath 未找到) add_subdirectory($ENV{CommonLibSSEPath_NG} CommonLibSSE EXCLUDE_FROM_ALL) endif()

find_package(spdlog CONFIG REQUIRED)
find_package(fmt CONFIG REQUIRED)
# 按功能：find_package(simpleini CONFIG REQUIRED) / find_package(directxtk CONFIG REQUIRED)

target_link_libraries(${PROJECT_NAME} PRIVATE
    spdlog::spdlog fmt::fmt CommonLibSSE::CommonLibSSE
    # 按功能：SimpleIni::SimpleIni / Microsoft::DirectXTK / d3d11 / dxgi
)

target_precompile_headers(${PROJECT_NAME} PRIVATE ${SOURCE_DIR}/pch.h)

# 安装：DLL → SKSE/Plugins（component main），PDB → /（component pdbs）
# COPY_OUTPUT：POST_BUILD copy_if_different 到 CompiledPluginsPath/SKSE/Plugins
```

> `find_dependency_path` 宏：先查 `extern/CommonLibSSE`（submodule 路径），未命中再查
> `$ENV{CommonLibSSEPath}` / `$ENV{CommonLibSSEPath_NG}`，随后 `add_subdirectory`。
> 两项目都用 `CommonLibSSE::CommonLibSSE` 目标。

## vcpkg.json（manifest 模式）

两个源项目共用基线 `cd61e1e26a038e82d6550a3ebbe0fbbfe7da78e3`，基础依赖：

```jsonc
{
  "name": "<lowercase-name>",
  "version": "<version>",
  "dependencies": [
    "fmt",
    "spdlog",
    { "name": "vcpkg-cmake-config", "host": true },
    "directxmath",
    "directxtk",
    // 按功能追加：simpleini（INI 配置）/ nlohmann-json / rapidcsv / toml11 / xbyak
  ],
  "builtin-baseline": "cd61e1e26a038e82d6550a3ebbe0fbbfe7da78e3"
}
```

## CMakePresets.json（受支持工作流）

三个隐藏 base + 一个对外 preset（两项目一致）：

```jsonc
{
  "configurePresets": [
    { "name": "cmake-dev", "binaryDir": "${sourceDir}/build",
      "cacheVariables": { "CMAKE_BUILD_TYPE": "Release" }, "hidden": true,
      "errors": { "deprecated": true }, "warnings": { "deprecated": true, "dev": true } },
    { "name": "vcpkg", "hidden": true,
      "cacheVariables": { "CMAKE_TOOLCHAIN_FILE": "$env{VCPKG_ROOT}/scripts/buildsystems/vcpkg.cmake" } },
    { "name": "windows", "hidden": true,
      "cacheVariables": {
        "CMAKE_MSVC_RUNTIME_LIBRARY": "MultiThreaded$<$<CONFIG:Debug>:Debug>DLL",
        "VCPKG_TARGET_TRIPLET": "x64-windows-static-md" } },
    { "name": "Release", "generator": "Visual Studio 17 2022",
      "architecture": { "strategy": "set", "value": "x64" },
      "toolset": "v143,version=14.44.35207",
      "cacheVariables": { "CMAKE_CXX_FLAGS": "/EHsc /MP /W4 /WX" },
      "inherits": ["cmake-dev", "vcpkg", "windows"] }
  ],
  "version": 3
}
```

- 本机路径（离线复用依赖目录、关闭 SKSE_SUPPORT_PATCH_SAFETY 等）放
  `CMakeUserPresets.json`，不提交。
- `x64-windows-static-md` 是 vcpkg triplet（动态 CRT 静态链接依赖）。

## 模块化约定

- 每个功能一个命名空间 + 一对 `h/cpp`（如 `Config`、`Input`、`ESPRenderer`、`Hooks`、
  `HitEvents`、`AllyFix`）。
- 头文件只声明稳定公共契约（`install()` / `load()` / `poll()` / `process_actor()` 等）。
- 新增模块 = 在 `src/` 加 `h/cpp` + 在 `src/CMakeLists.txt` 的 SOURCE/HEADER 列表登记 +
  在 `main.cpp` 相应生命周期点接线 + 按需在 `vcpkg.json` 加依赖。不要在无关文件中散落逻辑。
