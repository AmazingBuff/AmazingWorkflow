cmake_minimum_required(VERSION 3.22)

project({{PROJECT_NAME}} VERSION {{PROJECT_VERSION}} DESCRIPTION {{DESCRIPTION_CMAKE}} LANGUAGES CXX RC)
set(PROJECT_NAMESPACE {{NAMESPACE_CMAKE}})
set(PROJECT_AUTHOR {{AUTHOR_CMAKE}})

option(ENABLE_SKYRIM_SE "Enable Skyrim SE" {{ENABLE_SKYRIM_SE}})
option(ENABLE_SKYRIM_AE "Enable Skyrim AE" {{ENABLE_SKYRIM_AE}})
option(ENABLE_SKYRIM_VR "Enable Skyrim VR" {{ENABLE_SKYRIM_VR}})
option(BUILD_TESTS "Build CommonLib tests" OFF)
option(COPY_OUTPUT "Copy DLL/PDB to the configured mod Data root" OFF)
set(COMPILED_PLUGINS_PATH $ENV{COMPILED_PLUGINS_PATH} CACHE PATH "Mod Data root for COPY_OUTPUT")
set(COMMONLIBSSE_SOURCE_DIR $ENV{COMMONLIBSSE_SOURCE_DIR} CACHE PATH "Optional local CommonLib source")

if(PROJECT_SOURCE_DIR STREQUAL PROJECT_BINARY_DIR)
    message(FATAL_ERROR "Use an out-of-source build")
endif()
if(NOT WIN32 OR NOT CMAKE_SIZEOF_VOID_P EQUAL 8)
    message(FATAL_ERROR "SKSE requires Windows x64")
endif()
if(NOT ENABLE_SKYRIM_SE AND NOT ENABLE_SKYRIM_AE AND NOT ENABLE_SKYRIM_VR)
    message(FATAL_ERROR "Select at least one Skyrim runtime")
endif()
if(ENABLE_SKYRIM_VR AND {{FLAT_FEATURES_ENABLED}})
    message(FATAL_ERROR "The generated Present/Character hook examples require verified VR adaptations")
endif()

list(APPEND CMAKE_MODULE_PATH ${PROJECT_SOURCE_DIR}/cmake)
file(GLOB_RECURSE SOURCE_FILES CONFIGURE_DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/src/*.cpp)
file(GLOB_RECURSE HEADER_FILES CONFIGURE_DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/src/*.h)

set(VERSION_HEADER ${CMAKE_CURRENT_BINARY_DIR}/src/plugin.h)
configure_file(cmake/plugin.h.in ${VERSION_HEADER} @ONLY)
configure_file(cmake/version.rc.in ${CMAKE_CURRENT_BINARY_DIR}/version.rc @ONLY)
source_group(Source FILES ${SOURCE_FILES})
source_group(Header FILES ${HEADER_FILES} ${VERSION_HEADER})

add_library(${PROJECT_NAME} SHARED
    ${SOURCE_FILES} ${HEADER_FILES} ${VERSION_HEADER}
    ${CMAKE_CURRENT_BINARY_DIR}/version.rc
)
target_compile_features(${PROJECT_NAME} PRIVATE cxx_std_23)
if(MSVC)
    target_compile_options(${PROJECT_NAME} PRIVATE
        /EHsc /MP /W4 /WX /sdl /utf-8 /bigobj /permissive- /Zc:preprocessor
        /external:anglebrackets /external:W0 /wd4200
        $<$<CONFIG:Debug>:/ZI>
        $<$<CONFIG:Release>:/Zi;/Zc:inline;/JMC-;/Ob3>
    )
    target_link_options(${PROJECT_NAME} PRIVATE
        $<$<CONFIG:Debug>:/INCREMENTAL;/OPT:NOREF;/OPT:NOICF>
        $<$<CONFIG:Release>:/INCREMENTAL:NO;/OPT:REF;/OPT:ICF;/DEBUG:FULL>
    )
endif()
target_compile_definitions(${PROJECT_NAME} PRIVATE NOMINMAX)
target_include_directories(${PROJECT_NAME} PRIVATE
    ${CMAKE_CURRENT_BINARY_DIR}/src
    ${CMAKE_CURRENT_SOURCE_DIR}/src
)

if(EXISTS ${CMAKE_CURRENT_SOURCE_DIR}/extern/CommonLibSSE/CMakeLists.txt)
    set(commonlib_source ${CMAKE_CURRENT_SOURCE_DIR}/extern/CommonLibSSE)
elseif(COMMONLIBSSE_SOURCE_DIR AND EXISTS ${COMMONLIBSSE_SOURCE_DIR}/CMakeLists.txt)
    set(commonlib_source ${COMMONLIBSSE_SOURCE_DIR})
else()
    message(FATAL_ERROR "Initialize extern/CommonLibSSE or set COMMONLIBSSE_SOURCE_DIR")
endif()
add_subdirectory(${commonlib_source} ${CMAKE_CURRENT_BINARY_DIR}/extern/CommonLibSSE EXCLUDE_FROM_ALL)
find_package(spdlog CONFIG REQUIRED)
find_package(fmt CONFIG REQUIRED)
{{FEATURE_FIND_PACKAGES}}
target_link_libraries(${PROJECT_NAME} PRIVATE
    spdlog::spdlog fmt::fmt CommonLibSSE::CommonLibSSE
    {{FEATURE_LINK_LIBRARIES}}
)
target_precompile_headers(${PROJECT_NAME} PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/src/pch.h)

install(FILES $<TARGET_FILE:${PROJECT_NAME}> DESTINATION SKSE/Plugins COMPONENT main)
install(FILES $<TARGET_PDB_FILE:${PROJECT_NAME}> DESTINATION . COMPONENT pdbs)
install(FILES LICENSE README.md DESTINATION . COMPONENT main)
include(cmake/packaging.cmake)

if(COPY_OUTPUT)
    if(NOT COMPILED_PLUGINS_PATH)
        message(FATAL_ERROR "COPY_OUTPUT needs COMPILED_PLUGINS_PATH")
    endif()
    add_custom_command(TARGET ${PROJECT_NAME} POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E make_directory ${COMPILED_PLUGINS_PATH}/SKSE/Plugins
        COMMAND ${CMAKE_COMMAND} -E copy_if_different $<TARGET_FILE:${PROJECT_NAME}> ${COMPILED_PLUGINS_PATH}/SKSE/Plugins/
        COMMAND ${CMAKE_COMMAND} -E copy_if_different $<TARGET_PDB_FILE:${PROJECT_NAME}> ${COMPILED_PLUGINS_PATH}/SKSE/Plugins/
        VERBATIM
    )
endif()
