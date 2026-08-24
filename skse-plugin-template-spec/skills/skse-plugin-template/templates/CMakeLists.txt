cmake_minimum_required(VERSION 3.22)

project(
    {{PROJECT_NAME}}
    VERSION {{PROJECT_VERSION}}
    DESCRIPTION "{{DESCRIPTION}}"
    LANGUAGES CXX
)

if("${PROJECT_SOURCE_DIR}" STREQUAL "${PROJECT_BINARY_DIR}")
    message(FATAL_ERROR "in-source builds are not allowed")
endif()

macro(set_from_environment VARIABLE)
    if(NOT DEFINED ${VARIABLE} AND DEFINED ENV{${VARIABLE}})
        set(${VARIABLE} $ENV{${VARIABLE}})
    endif()
endmacro()

option(COPY_OUTPUT "Copy the output of build operations to the game directory" OFF)
option(ENABLE_SKYRIM_SE "Enable support for Skyrim SE in the dynamic runtime feature." {{ENABLE_SKYRIM_SE}})
option(ENABLE_SKYRIM_AE "Enable support for Skyrim AE in the dynamic runtime feature." {{ENABLE_SKYRIM_AE}})
option(ENABLE_SKYRIM_VR "Enable support for Skyrim VR in the dynamic runtime feature." {{ENABLE_SKYRIM_VR}})
# CommonLibSSE 自带单元测试（默认 ON）；本插件作为消费方默认关闭，
# 由 CommonLibSSE 的 option() 继承此值（先于 add_subdirectory 定义）。
option(BUILD_TESTS "Enable CommonLibSSE unit tests" OFF)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

if(COPY_OUTPUT)
    set_from_environment(CompiledPluginsPath)
    if(NOT DEFINED CompiledPluginsPath)
        message(FATAL_ERROR "CompiledPluginsPath is not set")
    endif()
endif()

list(APPEND CMAKE_MODULE_PATH "${PROJECT_SOURCE_DIR}/cmake")

add_subdirectory(src)
include(cmake/packaging.cmake)
