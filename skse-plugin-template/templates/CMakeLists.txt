cmake_minimum_required(VERSION 3.25)

project(
    {{PROJECT_NAME}}
    VERSION {{PROJECT_VERSION}}
    DESCRIPTION "{{DESCRIPTION_CMAKE}}"
    LANGUAGES CXX
)

option(COPY_OUTPUT "Copy the output of build operations to the game directory" OFF)
option(ENABLE_SKYRIM_SE "Enable support for Skyrim SE in the dynamic runtime feature." {{ENABLE_SKYRIM_SE}})
option(ENABLE_SKYRIM_AE "Enable support for Skyrim AE in the dynamic runtime feature." {{ENABLE_SKYRIM_AE}})
option(ENABLE_SKYRIM_VR "Enable support for Skyrim VR in the dynamic runtime feature." {{ENABLE_SKYRIM_VR}})
option(BUILD_TESTS "Enable CommonLibSSE unit tests" OFF)

set(PROJECT_AUTHOR "{{AUTHOR_CMAKE}}")
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

set(
    COMPILED_PLUGINS_PATH
    "$ENV{COMPILED_PLUGINS_PATH}"
    CACHE PATH
    "Optional output root used only when COPY_OUTPUT is enabled"
)
set(
    COMMONLIBSSE_SOURCE_DIR
    "$ENV{COMMONLIBSSE_SOURCE_DIR}"
    CACHE PATH
    "Optional local CommonLibSSE-NG ng source directory"
)

list(APPEND CMAKE_MODULE_PATH "${PROJECT_SOURCE_DIR}/cmake")

if("${PROJECT_SOURCE_DIR}" STREQUAL "${PROJECT_BINARY_DIR}")
    message(FATAL_ERROR "in-source builds are not allowed")
endif()

if(COPY_OUTPUT AND NOT COMPILED_PLUGINS_PATH)
    message(FATAL_ERROR "COMPILED_PLUGINS_PATH is not set")
endif()

if(EXISTS "${PROJECT_SOURCE_DIR}/ext/CommonLibSSE/CMakeLists.txt")
    set(commonlibsse_source_dir "${PROJECT_SOURCE_DIR}/ext/CommonLibSSE")
elseif(COMMONLIBSSE_SOURCE_DIR AND EXISTS "${COMMONLIBSSE_SOURCE_DIR}/CMakeLists.txt")
    set(commonlibsse_source_dir "${COMMONLIBSSE_SOURCE_DIR}")
else()
    message(
        FATAL_ERROR
        "CommonLibSSE-NG was not found. Run: git submodule add -b ng "
        "https://github.com/alandtse/CommonLibSSE-NG.git ext/CommonLibSSE"
    )
endif()

add_subdirectory(
    "${commonlibsse_source_dir}"
    "${CMAKE_CURRENT_BINARY_DIR}/_deps/CommonLibSSE"
    EXCLUDE_FROM_ALL
)
add_subdirectory(src)
include(cmake/packaging.cmake)
