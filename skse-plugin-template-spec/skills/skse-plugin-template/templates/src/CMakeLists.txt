set(ROOT_DIR "${CMAKE_CURRENT_SOURCE_DIR}/..")
set(SOURCE_DIR "${ROOT_DIR}/src")

set(SOURCE_FILES
    {{SOURCE_FILES}}
)
set(HEADER_FILES
    {{HEADER_FILES}}
)

set(VERSION_HEADER "${CMAKE_CURRENT_BINARY_DIR}/src/Plugin.h")
configure_file(
    "${ROOT_DIR}/cmake/Plugin.h.in"
    "${VERSION_HEADER}"
    @ONLY
)
configure_file(
    "${ROOT_DIR}/cmake/version.rc.in"
    "${CMAKE_CURRENT_BINARY_DIR}/version.rc"
    @ONLY
)

{{FEATURE_FIND_PACKAGES}}

add_commonlibsse_plugin(
    ${PROJECT_NAME}
    AUTHOR "${PROJECT_AUTHOR}"
    USE_ADDRESS_LIBRARY
    SOURCES
        ${HEADER_FILES}
        ${SOURCE_FILES}
        ${VERSION_HEADER}
        ${CMAKE_CURRENT_BINARY_DIR}/version.rc
)

source_group("Source" FILES ${SOURCE_FILES})
source_group("Header" FILES ${HEADER_FILES} ${VERSION_HEADER})

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
    ${CMAKE_CURRENT_BINARY_DIR}/src
    ${SOURCE_DIR}
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
    ${SOURCE_DIR}/pch.h
)

install(
    FILES "$<TARGET_FILE:${PROJECT_NAME}>"
    DESTINATION "SKSE/Plugins"
    COMPONENT "main"
)
install(
    FILES "$<TARGET_PDB_FILE:${PROJECT_NAME}>"
    DESTINATION "."
    COMPONENT "pdbs"
)

if(COPY_OUTPUT)
    add_custom_command(
        TARGET ${PROJECT_NAME}
        POST_BUILD
        COMMAND
            "${CMAKE_COMMAND}" -E make_directory "${CompiledPluginsPath}/SKSE/Plugins"
        COMMAND
            "${CMAKE_COMMAND}" -E copy_if_different
            "$<TARGET_FILE:${PROJECT_NAME}>"
            "${CompiledPluginsPath}/SKSE/Plugins/"
        COMMAND
            "${CMAKE_COMMAND}" -E copy_if_different
            "$<TARGET_PDB_FILE:${PROJECT_NAME}>"
            "${CompiledPluginsPath}/SKSE/Plugins/"
        VERBATIM
    )
endif()
