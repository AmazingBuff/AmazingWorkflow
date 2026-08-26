set(source_dir "${PROJECT_SOURCE_DIR}/src")
set(generated_dir "${CMAKE_CURRENT_BINARY_DIR}/generated")

set(source_files
    {{SOURCE_FILES}}
)
set(header_files
    {{HEADER_FILES}}
)

set(plugin_header "${generated_dir}/plugin.h")
set(version_resource "${generated_dir}/version.rc")
file(MAKE_DIRECTORY "${generated_dir}")
configure_file(
    "${PROJECT_SOURCE_DIR}/cmake/plugin_version.h.in"
    "${plugin_header}"
    @ONLY
)
configure_file(
    "${PROJECT_SOURCE_DIR}/cmake/version.rc.in"
    "${version_resource}"
    @ONLY
)

{{FEATURE_FIND_PACKAGES}}

add_commonlibsse_plugin(
    ${PROJECT_NAME}
    AUTHOR "${PROJECT_AUTHOR}"
    USE_ADDRESS_LIBRARY
    SOURCES
    ${header_files}
    ${source_files}
    ${plugin_header}
    ${version_resource}
)

source_group("Source" FILES ${source_files})
source_group("Header" FILES ${header_files} ${plugin_header})

target_compile_features(
    ${PROJECT_NAME}
    PRIVATE
    cxx_std_23
)

if(MSVC)
    target_compile_options(
        ${PROJECT_NAME}
        PRIVATE
        /EHsc
        /MP
        /W4
        /WX
        /bigobj
        /external:anglebrackets
        /external:W0
        /permissive-
        /sdl
        /utf-8
        /Zc:preprocessor
        "$<$<CONFIG:Debug>:/ZI>"
        "$<$<NOT:$<CONFIG:Debug>>:/Zi>"
        "$<$<CONFIG:Release>:/JMC->"
    )
    target_link_options(
        ${PROJECT_NAME}
        PRIVATE
        "$<$<CONFIG:Debug>:/INCREMENTAL;/OPT:NOREF;/OPT:NOICF>"
        "$<$<CONFIG:Release>:/INCREMENTAL:NO;/OPT:REF;/OPT:ICF;/DEBUG:FULL>"
    )
endif()

target_compile_definitions(
    ${PROJECT_NAME}
    PRIVATE
    NOMINMAX
    WIN32_LEAN_AND_MEAN
)
target_include_directories(
    ${PROJECT_NAME}
    PRIVATE
    ${generated_dir}
    ${source_dir}
    {{FEATURE_INCLUDE_DIRECTORIES}}
)
target_link_libraries(
    ${PROJECT_NAME}
    PRIVATE
    {{FEATURE_LINK_LIBRARIES}}
)
target_precompile_headers(
    ${PROJECT_NAME}
    PRIVATE
    ${source_dir}/pch.h
)

install(
    FILES
    "$<TARGET_FILE:${PROJECT_NAME}>"
    DESTINATION
    "SKSE/Plugins"
    COMPONENT
    "main"
)
install(
    FILES
    "$<TARGET_PDB_FILE:${PROJECT_NAME}>"
    DESTINATION
    "."
    COMPONENT
    "pdbs"
)

if(COPY_OUTPUT)
    add_custom_command(
        TARGET
        ${PROJECT_NAME}
        POST_BUILD
        COMMAND
        "${CMAKE_COMMAND}" -E make_directory "${COMPILED_PLUGINS_PATH}/SKSE/Plugins"
        COMMAND
        "${CMAKE_COMMAND}" -E copy_if_different
        "$<TARGET_FILE:${PROJECT_NAME}>"
        "${COMPILED_PLUGINS_PATH}/SKSE/Plugins/"
        COMMAND
        "${CMAKE_COMMAND}" -E copy_if_different
        "$<TARGET_PDB_FILE:${PROJECT_NAME}>"
        "${COMPILED_PLUGINS_PATH}/SKSE/Plugins/"
        VERBATIM
    )
endif()
