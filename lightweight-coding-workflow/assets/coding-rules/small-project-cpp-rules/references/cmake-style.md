# CMake 工程规则

## 目录

- 适配原则
- 文件结构与根文件编排
- 命名与格式
- 项目声明与目标属性
- 函数与自定义命令
- 第三方库管理
- 平台、安装与导出
- CMakePresets.json
- 验证与禁止项

## 适配原则

先读取现有 `CMakeLists.txt`、`CMakePresets.json`、toolchain、包管理清单、格式化约定和 CI。保持受支持的 CMake 版本、生成器、平台、目标名和安装布局；不要把工具链升级、全局格式化或目录重排夹带在功能修改中。

以下规则是用户指定的 CMake 规范基线，默认用于绿地项目以及新增或实际触及的构建文件。既有项目的兼容性和正式配置按 `decision-policy.md` 裁决，并只修改本次任务需要的最小范围。

## 文件结构与根文件编排

- 每个子目录使用一个 `CMakeLists.txt`，由父级通过 `add_subdirectory()` 引入。
- 子目录内的自定义函数使用 `function()` / `endfunction()`，并紧跟在相关目标定义之后。
- 根 `CMakeLists.txt` 按以下顺序组织适用项：

1. `cmake_minimum_required(VERSION 3.25)`
2. `project()`
3. `option()`
4. 全局 `set()` 变量
5. 编译器检测与编译选项
6. `add_subdirectory()` 子目录
7. `find_package()` 外部依赖
8. `file(GLOB_RECURSE ...)` 源文件收集
9. `add_library()` / `add_executable()` 目标定义
10. `target_sources()`
11. `target_include_directories()`
12. `target_precompile_headers()`
13. `target_link_libraries()`
14. `target_compile_features()`
15. `target_compile_definitions()`
16. `add_custom_command()`
17. 平台特定分支（例如 `if(WIN32)`）
18. 构建后钩子 / 自定义函数调用

顺序服务于可读性；依赖拓扑确实要求先定义时，做最小调整并保持目标作用域清晰。新项目优先显式列出第一方源文件；既有项目已使用 glob 时保持一致，新 glob 限定在第一方目录并使用 `CONFIGURE_DEPENDS`。

## 命名与格式

### 命名

| 类别 | 规则 | 示例 |
|---|---|---|
| CMake 函数名 | `snake_case` | `add_sample()`, `add_rendering_sample()` |
| CMake 自定义宏/函数 | `snake_case` | `add_include_dirs()`, `execute_reflect()` |
| Project / target 名 | `snake_case` 或 `PascalCase` | `engine`, `rendering_common` |
| 缓存变量 | `UPPER_SNAKE_CASE` | `THIRD_PARTY_LIBS`, `CMAKE_BUILD_TYPE` |
| 函数局部变量 | `snake_case` | `current_libs`, `source_files` |
| 函数参数 | `snake_case` | `target`, `lib_name` |
| CMake preset 名 | 全小写 + 空格分隔 | `msvc debug`, `clang release` |

### 命令、缩进与多行调用

- CMake 命令名使用全小写，左括号紧跟命令名：`add_library(...)`。
- 参数少时单行书写；参数多时每行一个参数，闭括号独立并与命令首列对齐。
- `if(WIN32)`、`foreach(sample ${sample_list})`、`function(add_sample sample_name)` 等条件、循环和函数调用遵循同一括号风格；逻辑运算符使用大写 `AND`、`OR`、`NOT`。
- `function()`、`if()`、`foreach()` 体内统一缩进 4 个空格；禁止 Tab 和行尾空格。
- 可见性关键字（`PUBLIC`、`PRIVATE`、`INTERFACE`）独占一行，与参数列表对齐。

```cmake
add_subdirectory(ext)
add_subdirectory(3rd)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

target_link_libraries(
    ${PROJECT_NAME}
    PUBLIC
    ${THIRD_PARTY_LIBS}
    SDL3::SDL3
    Eigen3::Eigen
)

target_compile_definitions(
    ${PROJECT_NAME}
    PUBLIC
    NOMINMAX
    WIN32_LEAN_AND_MEAN
)
```

## 项目声明与目标属性

绿地项目的默认声明如下；既有项目保持已验证的最低 CMake 版本和语言标准：

```cmake
cmake_minimum_required(VERSION 3.25)

project(
    my_project
    LANGUAGES CXX C
    DESCRIPTION "brief description"
)

option(BUILD_SHARED_LIBS "Build shared libraries" OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
```

`option()` 紧跟 `project()`；`CMAKE_EXPORT_COMPILE_COMMANDS` 始终开启。

所有目标属性使用 `target_*` 系列命令，禁止使用全局 `include_directories()`、`link_libraries()` 和 `add_definitions()`：

```cmake
add_library(${PROJECT_NAME} STATIC)

target_sources(
    ${PROJECT_NAME}
    PRIVATE
    ${HEADER_FILES}
    ${SOURCE_FILES}
)

target_include_directories(
    ${PROJECT_NAME}
    PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include/
    PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/src/
)

target_precompile_headers(
    ${PROJECT_NAME}
    PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/src/pch.h
)

target_compile_features(
    ${PROJECT_NAME}
    PUBLIC
    cxx_std_23
)
```

- 每个目标只定义一次；子目录只能扩展已知目标或定义独立目标。
- 公共头需要的依赖使用 `PUBLIC`，仅实现需要的使用 `PRIVATE`，header-only 消费需求使用 `INTERFACE`。
- 不用全局编译选项解决单个目标的问题；稳定库可提供 namespaced alias，例如 `add_library(Project::Target ALIAS target)`。
- 目标名、输出名和导出名是不同概念；不要为视觉统一破坏消费方。
- 生成文件写入 binary tree，不污染源码树；路径使用引号和 CMake 路径语义，不硬编码本机绝对路径。

## 函数与自定义命令

自定义函数使用小写 `snake_case`；函数参数和局部变量也使用 `snake_case`。函数内引用 `${PROJECT_NAME}`，不要硬编码项目名；列表参数使用 `foreach()` 分派：

```cmake
function(add_sample sample_name)
    file(GLOB_RECURSE source_files ${sample_name}/*.cpp)

    set(CMAKE_RUNTIME_OUTPUT_DIRECTORY_DEBUG   ${CMAKE_CURRENT_BINARY_DIR}/${sample_name})
    set(CMAKE_RUNTIME_OUTPUT_DIRECTORY_RELEASE ${CMAKE_CURRENT_BINARY_DIR}/${sample_name})

    add_executable(${sample_name})
    target_sources(${sample_name} PRIVATE ${source_files})
    target_link_libraries(${sample_name} PUBLIC ${PROJECT_NAME})
endfunction()

function(add_samples sample_list)
    foreach(sample ${sample_list})
        add_sample(${sample})
    endforeach()
endfunction()
```

`add_custom_command()` 使用多行形式。目标型 post-build 命令的关键字独占一行，并用生成器表达式引用输出目录：

```cmake
add_custom_command(
    TARGET
    ${sample_name}
    POST_BUILD
    COMMAND
    ${CMAKE_COMMAND} -E copy_if_different ${THIRD_PARTY_DLLS} $<TARGET_FILE_DIR:${sample_name}>
    VERBATIM
)
```

产生文件的自定义命令还必须声明 `OUTPUT` 或 `BYPRODUCTS`、`DEPENDS` 和消费目标；代码生成工具与运行时库使用独立目标，生成目录通过目标作用域传递。

## 第三方库管理

- 预编译第三方库放在 `3rd/`，通过封装的 `add_lib()` 导入。
- 源码级第三方依赖使用 Git submodule 放在 `ext/`，在 `ext/CMakeLists.txt` 中用 `add_subdirectory()` 引入。
- 使用 `CACHE STRING` 变量在层级间传递库路径；一个依赖只设一个权威来源。
- 优先消费上游导出的 CMake target，而不是手工拼 include 和 library 路径。外部依赖的 `SYSTEM` include 只用于抑制第三方诊断，不得掩盖第一方警告。
- 复制运行时文件使用 target-aware generator expressions，不硬编码输出目录。

```cmake
function(add_lib lib_name libs dlls include_dirs)
    set(current_libs "${${libs}}")
    set(current_dlls "${${dlls}}")
    set(current_include_dirs "${${include_dirs}}")

    if(WIN32)
        file(GLOB LIBS ${lib_name}/lib/x64/*.lib)
        file(GLOB DLLS ${lib_name}/bin/x64/*.dll)
    endif()

    list(APPEND current_libs ${LIBS})
    list(APPEND current_dlls ${DLLS})
    list(APPEND current_include_dirs ${CMAKE_CURRENT_SOURCE_DIR}/${lib_name}/include/)

    set(${libs} ${current_libs} PARENT_SCOPE)
    set(${dlls} ${current_dlls} PARENT_SCOPE)
    set(${include_dirs} ${current_include_dirs} PARENT_SCOPE)
endfunction()

add_lib(dxc LIBS DLLS INCLUDE_DIRS)
add_lib(vulkan LIBS DLLS INCLUDE_DIRS)

set(THIRD_PARTY_LIBS ${LIBS} CACHE STRING "" FORCE)
set(THIRD_PARTY_DLLS ${DLLS} CACHE STRING "" FORCE)
set(THIRD_PARTY_INCLUDE_DIRS ${INCLUDE_DIRS} CACHE STRING "" FORCE)
```

锁定依赖版本时记录兼容范围和更新机制；安装接口不得泄漏私有依赖。

## 平台、安装与导出

- 把平台判断集中在构建或适配层，不散落到无关目标；优先 capability check，而不是只判断操作系统名称。
- 编译器特定选项放在明确条件中，并说明它解决的兼容问题；多配置生成器不要依赖 `CMAKE_BUILD_TYPE`，用 generator expressions 或 preset 配置。
- 仅在目标需要被外部消费时增加安装规则：安装公共头、库、运行时文件和 package config。
- 通过 build/install interface 分离源码路径与安装路径；共享库显式管理符号可见性和导出宏。
- 导出的 target 使用稳定 namespace，避免暴露构建树内部目标；使用安装后的最小消费项目验证 package，而不只验证源码树链接。

## CMakePresets.json

使用 `CMakePresets.json` 管理受支持的构建配置，而不是把重复配置散落在命令行。绿地 Windows/MSVC 基线如下：

```json
{
    "version": 3,
    "configurePresets": [
        {
            "name": "msvc",
            "hidden": true,
            "generator": "Ninja",
            "binaryDir": "${sourceDir}/build/${presetName}",
            "installDir": "${sourceDir}/install/${presetName}",
            "cacheVariables": {
                "CMAKE_C_COMPILER": "cl.exe",
                "CMAKE_CXX_COMPILER": "cl.exe"
            },
            "condition": {
                "type": "equals",
                "lhs": "${hostSystemName}",
                "rhs": "Windows"
            }
        },
        {
            "name": "msvc debug",
            "displayName": "MSVC Debug",
            "inherits": "msvc",
            "architecture": {
                "value": "x64",
                "strategy": "external"
            },
            "cacheVariables": {
                "CMAKE_BUILD_TYPE": "Debug"
            }
        },
        {
            "name": "msvc release",
            "displayName": "MSVC Release",
            "inherits": "msvc debug",
            "cacheVariables": {
                "CMAKE_BUILD_TYPE": "Release"
            }
        }
    ]
}
```

预设规则：

- 使用 `"version": 3`；基础编译器预设标记 `"hidden": true`。
- 使用 `"inherits"` 继承基础预设；至少提供 debug 和 release 两个受支持配置。
- `binaryDir` 使用 `${sourceDir}/build/${presetName}`，`installDir` 使用 `${sourceDir}/install/${presetName}`。
- 使用 `condition` 限制平台适用性；生成器固定为 `Ninja`，除非既有项目已有受支持的生成器约束。
- 个人本机路径放在 `CMakeUserPresets.json`，不提交到共享 preset。
- schema 版本与项目最低 CMake 版本兼容，不枚举未经验证的编译器组合。

## 验证与禁止项

按项目支持的 workflow 运行：

```text
cmake --preset <configure-preset>
cmake --build --preset <build-preset>
ctest --preset <test-preset> --output-on-failure
```

没有 presets 时使用明确的 `-S`、`-B`、generator 和 toolchain 参数。至少验证一个受支持配置；涉及平台、编译选项、依赖或公开安装接口时扩大到对应矩阵。不要声称未运行的编译器、SDK 或配置已通过。

禁止：

- 使用全局 `include_directories()`、`link_libraries()` 或 `add_definitions()`。
- 把 CMake 命令写成缺少实际参数的 `add_library(name)`；需要参数时显式展开 `add_library(name ...)`。
- 使用硬编码本机绝对路径、硬编码输出目录或未经声明依赖的生成步骤。
- 用全局设置掩盖单个目标的问题，或从 vendor、生成文件、构建产物和复制示例推断第一方风格。
- 为符合本 skill 批量重写未触及的 `CMakeLists.txt`、presets 或依赖配置。
