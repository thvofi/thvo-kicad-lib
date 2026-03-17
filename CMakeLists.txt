cmake_minimum_required( VERSION 3.12 FATAL_ERROR )

project( kicad-symbols NONE )

#================================================
# Locations for install targets.
#================================================
if( APPLE )
    # Like all variables, CMAKE_INSTALL_PREFIX can be over-ridden on the command line.
    set( CMAKE_INSTALL_PREFIX "/Library/Application Support/kicad/" CACHE PATH "" )

    # Everything without leading / is relative to CMAKE_INSTALL_PREFIX.
    set( KICAD_LIBRARY symbols )
    set( KICAD_TEMPLATE template )
else()
    # Everything without leading / is relative to CMAKE_INSTALL_PREFIX.
    set( KICAD_DATA share/kicad
         CACHE PATH "Location of KiCad data files." )
    set( KICAD_LIBRARY ${KICAD_DATA}/symbols )
    set( KICAD_TEMPLATE ${KICAD_DATA}/template )
endif()

mark_as_advanced( KICAD_DATA KICAD_LIBRARY )

option(KICAD_PACK_SYM_LIBRARIES "Pack symbol libraries before installation" ON)


#================================================
# "make uninstall" rules
#================================================
configure_file(
    "${PROJECT_SOURCE_DIR}/CMakeModules/cmake_uninstall.cmake.in"
    "${CMAKE_CURRENT_BINARY_DIR}/cmake_uninstall.cmake"
    IMMEDIATE @ONLY
)

add_custom_target( uninstall
    "${CMAKE_COMMAND}" -P "${CMAKE_CURRENT_BINARY_DIR}/cmake_uninstall.cmake"
)


#================================================
# Functions to pack symbol libraries.
#================================================

find_package(Python3 COMPONENTS Interpreter)

# Pack all libraries in a list
#
# Arguments:
#   input_libs       - List of input library directories to pack
#   output_dir       - Directory to place packed library files
#   packed_lib_files - Output variable to receive list of packed library files
#   sym_lib_table    - Symbol library table file to update with packed libraries
function( pack_all_libraries input_libs output_dir packed_lib_files sym_lib_table packed_sym_lib_table )

    set( local_packed_lib_files "" )

    if( NOT Python3_FOUND )
        message( FATAL_ERROR "Python3 not found. Cannot pack symbol libraries." )
    endif()

    # Collect all source files inside the library directories
    set( all_source_files "" )
    foreach( lib_dir ${input_libs} )
        file( GLOB lib_source_files "${lib_dir}/*.kicad_sym" )
        list( APPEND all_source_files ${lib_source_files} )
    endforeach()

    foreach( lib_file ${input_libs} )
        get_filename_component( lib_name ${lib_file} NAME_WE )
        set( packed_lib_file "${output_dir}/${lib_name}.kicad_sym" )
        list( APPEND local_packed_lib_files ${packed_lib_file} )
    endforeach()

    set( local_packed_sym_lib_table "${output_dir}/sym-lib-table" )

    set( pack_script "${CMAKE_CURRENT_SOURCE_DIR}/tools/kicad_lib_pack.py" )

    add_custom_command(
        OUTPUT
            ${local_packed_lib_files}
            ${local_packed_sym_lib_table}
        COMMAND ${CMAKE_COMMAND} -E make_directory ${output_dir}
        COMMAND ${Python3_EXECUTABLE} "${pack_script}"
            --input ${input_libs}
            --output "${output_dir}"
            --table "${sym_lib_table}"
            -v
        DEPENDS
            ${all_source_files}
            ${sym_lib_table}
            ${pack_script}
        COMMENT "Packing symbol libraries and table to ${output_dir}"
        VERBATIM
    )

    set( ${packed_lib_files} ${local_packed_lib_files} PARENT_SCOPE )
    set( ${packed_sym_lib_table} ${local_packed_sym_lib_table} PARENT_SCOPE )
endfunction()

#================================================
# Library pre-flighting - e.g. packing
#================================================

# Install all of the symbol library (.kicad_sym) and simulation model (.sp)
# files in this folder.

file( GLOB sym_lib_dirs "*.kicad_symdir" )
file( GLOB sym_lib_files "*.kicad_sym" )
file( GLOB sym_sim_files "*.sp" )

if( KICAD_PACK_SYM_LIBRARIES )
    message( STATUS "Packing libraries before installation")

    if( NOT sym_lib_dirs )
        message( FATAL_ERROR "No unpacked symbol library directories found. Cannot pack symbol libraries." )
    endif()

    set( packed_lib_dir "${CMAKE_CURRENT_BINARY_DIR}/packed" )


    # Pack all symbol libraries before installation.
    # This has a limitation that you have to run CMake after adding new libraries
    # but this should be fine for packaging and installation use cases.
    set( packed_sym_lib_files "" )
    set( packed_sym_lib_table "" )
    pack_all_libraries(
        "${sym_lib_dirs}"
        "${packed_lib_dir}"
        packed_sym_lib_files
        "${CMAKE_SOURCE_DIR}/sym-lib-table"
        packed_sym_lib_table
    )

    # The pack target depends on all packed libraries.
    add_custom_target( pack_symbols
        ALL # make pack_symbols part of the default build
        DEPENDS
            ${packed_sym_lib_files}
            ${packed_sym_lib_table}
    )

    set( installed_sym_lib_files ${packed_sym_lib_files} )
    set( installed_sym_lib_dirs "" )
    set( installed_sym_lib_table "${packed_sym_lib_table}" )

else()
    message( STATUS "Not packing libraries before installation" )

    if( sym_lib_dirs )
        # If we have library directories, we install as directories.
        set( installed_sym_lib_files "" )
        set( installed_sym_lib_dirs ${sym_lib_dirs} )
    else()
        # If we don't have library directories, we install individual files as libraries
        set( installed_sym_lib_files ${sym_lib_files} )
        set( installed_sym_lib_dirs "" )
    endif()

    # Use the original sym-lib-table in both cases, since it should
    # already be correct for the branch.
    set( installed_sym_lib_table "sym-lib-table" )
endif()

#================================================
# Installed files.
#================================================

# Install symbol libraries as files and/or directories

install(
    DIRECTORY ${installed_sym_lib_dirs}
    DESTINATION ${KICAD_LIBRARY}
    COMPONENT resources
)

install (
    FILES
        ${installed_sym_lib_files}
        ${sym_sim_files}
    DESTINATION ${KICAD_LIBRARY}
    COMPONENT resources
)

# Install the default global symbol library table in the template folder.
install(
    FILES ${installed_sym_lib_table}
    DESTINATION ${KICAD_TEMPLATE}
    COMPONENT resources
)
