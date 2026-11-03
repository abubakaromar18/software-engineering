cmake_minimum_required(VERSION 3.20)
project(composite_file_tree VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

option(VFS_BUILD_TESTS "Build the unit tests (uses system GoogleTest or fetches it)" ON)
option(VFS_WARNINGS_AS_ERRORS "Treat compiler warnings as errors" ON)

# ---- Library ---------------------------------------------------------------
add_library(vfs
    src/node.cpp
    src/visitors.cpp
    src/text.cpp
    src/manifest.cpp
    src/cli.cpp
)
target_include_directories(vfs PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)

if(MSVC)
    target_compile_options(vfs PRIVATE /W4 $<$<BOOL:${VFS_WARNINGS_AS_ERRORS}>:/WX>)
else()
    target_compile_options(vfs PRIVATE -Wall -Wextra -Wpedantic -Wconversion -Wshadow
        $<$<BOOL:${VFS_WARNINGS_AS_ERRORS}>:-Werror>)
endif()

# ---- CLI -------------------------------------------------------------------
add_executable(vfs-tree src/main.cpp)
target_link_libraries(vfs-tree PRIVATE vfs)

# ---- Tests -----------------------------------------------------------------
if(VFS_BUILD_TESTS)
    # Prefer an installed GoogleTest (e.g. apt's libgtest-dev); otherwise
    # download a pinned release.
    find_package(GTest 1.14 QUIET)
    if(NOT GTest_FOUND)
        include(FetchContent)
        FetchContent_Declare(
            googletest
            URL https://github.com/google/googletest/archive/refs/tags/v1.15.2.tar.gz
            DOWNLOAD_EXTRACT_TIMESTAMP TRUE
        )
        set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
        set(INSTALL_GTEST OFF CACHE BOOL "" FORCE)
        FetchContent_MakeAvailable(googletest)
    endif()

    enable_testing()
    add_executable(vfs_tests
        tests/test_node.cpp
        tests/test_visitors.cpp
        tests/test_text.cpp
        tests/test_manifest.cpp
        tests/test_cli.cpp
    )
    target_link_libraries(vfs_tests PRIVATE vfs GTest::gtest_main)
    target_compile_definitions(vfs_tests PRIVATE
        VFS_EXAMPLE_MANIFEST="${CMAKE_CURRENT_SOURCE_DIR}/examples/project.manifest")
    include(GoogleTest)
    gtest_discover_tests(vfs_tests)
endif()
