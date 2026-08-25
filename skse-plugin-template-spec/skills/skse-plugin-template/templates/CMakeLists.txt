cmake_minimum_required(VERSION 3.22)

project(
    {{PROJECT_NAME}}
    VERSION {{PROJECT_VERSION}}
    DESCRIPTION "{{DESCRIPTION_CMAKE}}"
    LANGUAGES CXX
)

set(PROJECT_AUTHOR "{{AUTHOR_CMAKE}}")

if("${PROJECT_SOURCE_DIR}" STREQUAL "${PROJECT_BINARY_DIR}")
    message(FATAL_ERROR "in-source builds are not allowed")
endif()

option(COPY_OUTPUT "Copy the output of build operations to the game directory" OFF)
option(ENABLE_SKYRIM_SE "Enable support for Skyrim SE in the dynamic runtime feature." {{ENABLE_SKYRIM_SE}})
option(ENABLE_SKYRIM_AE "Enable support for Skyrim AE in the dynamic runtime feature." {{ENABLE_SKYRIM_AE}})
option(ENABLE_SKYRIM_VR "Enable support for Skyrim VR in the dynamic runtime feature." {{ENABLE_SKYRIM_VR}})
option(BUILD_TESTS "Enable CommonLibSSE unit tests" OFF)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

set(
    CompiledPluginsPath
    "$ENV{CompiledPluginsPath}"
    CACHE PATH
    "Optional output root used only when COPY_OUTPUT is enabled"
)
if(COPY_OUTPUT)
    if(NOT CompiledPluginsPath)
        message(FATAL_ERROR "CompiledPluginsPath is not set")
    endif()
endif()

list(APPEND CMAKE_MODULE_PATH "${PROJECT_SOURCE_DIR}/cmake")

set(
    CommonLibSSEPath_NG
    "$ENV{CommonLibSSEPath_NG}"
    CACHE PATH
    "Optional local CommonLibSSE-NG ng source directory"
)
if(EXISTS "${PROJECT_SOURCE_DIR}/extern/CommonLibSSE/CMakeLists.txt")
    set(commonlibsse_source_dir "${PROJECT_SOURCE_DIR}/extern/CommonLibSSE")
elseif(CommonLibSSEPath_NG AND EXISTS "${CommonLibSSEPath_NG}/CMakeLists.txt")
    set(commonlibsse_source_dir "${CommonLibSSEPath_NG}")
else()
    message(
        FATAL_ERROR
        "CommonLibSSE-NG was not found. Run: git submodule add -b ng "
        "https://github.com/alandtse/CommonLibSSE-NG.git extern/CommonLibSSE"
    )
endif()

add_subdirectory(
    "${commonlibsse_source_dir}"
    "${CMAKE_CURRENT_BINARY_DIR}/_deps/CommonLibSSE"
    EXCLUDE_FROM_ALL
)
add_subdirectory(src)
include(cmake/packaging.cmake)
