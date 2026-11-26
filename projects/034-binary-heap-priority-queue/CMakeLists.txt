cmake_minimum_required(VERSION 3.20)
project(heapq VERSION 1.0.0 DESCRIPTION "Binary heap, indexed priority queue and heapsort" LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

option(HEAPQ_BUILD_TESTS "Build the GoogleTest suite" ON)
option(HEAPQ_BUILD_DEMO "Build the task scheduler demo" ON)
option(HEAPQ_SANITIZE "Build with AddressSanitizer and UBSan" OFF)

# Shared warning/sanitizer flags, applied to our own targets only.
add_library(heapq_project_options INTERFACE)
if(MSVC)
  target_compile_options(heapq_project_options INTERFACE /W4 /permissive-)
else()
  target_compile_options(heapq_project_options INTERFACE -Wall -Wextra -Wpedantic -Wshadow -Wconversion -Wsign-conversion)
  if(HEAPQ_SANITIZE)
    target_compile_options(heapq_project_options INTERFACE -fsanitize=address,undefined -fno-omit-frame-pointer)
    target_link_options(heapq_project_options INTERFACE -fsanitize=address,undefined)
  endif()
endif()

# The library itself is header-only.
add_library(heapq INTERFACE)
add_library(heapq::heapq ALIAS heapq)
target_include_directories(heapq INTERFACE
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>)
target_compile_features(heapq INTERFACE cxx_std_20)

if(HEAPQ_BUILD_DEMO OR HEAPQ_BUILD_TESTS)
  add_library(heap_scheduler_lib STATIC demo/scheduler.cpp)
  target_include_directories(heap_scheduler_lib PUBLIC demo)
  target_link_libraries(heap_scheduler_lib PUBLIC heapq PRIVATE heapq_project_options)
endif()

if(HEAPQ_BUILD_DEMO)
  add_executable(heap_scheduler demo/main.cpp)
  target_link_libraries(heap_scheduler PRIVATE heap_scheduler_lib heapq_project_options)
endif()

if(HEAPQ_BUILD_TESTS)
  enable_testing()
  # Prefer a system GoogleTest, otherwise fetch a pinned release.
  find_package(GTest 1.14 CONFIG QUIET)
  if(NOT GTest_FOUND)
    include(FetchContent)
    FetchContent_Declare(googletest
      GIT_REPOSITORY https://github.com/google/googletest.git
      GIT_TAG b514bdc898e2951020cbdca1304b75f5950d1f59 # v1.15.2
      GIT_SHALLOW FALSE)
    set(INSTALL_GTEST OFF CACHE BOOL "" FORCE)
    set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
    FetchContent_MakeAvailable(googletest)
  endif()

  add_executable(heapq_tests
    tests/binary_heap_test.cpp
    tests/indexed_heap_test.cpp
    tests/heap_sort_test.cpp
    tests/scheduler_test.cpp)
  target_link_libraries(heapq_tests PRIVATE heapq heap_scheduler_lib heapq_project_options GTest::gtest_main)

  include(GoogleTest)
  gtest_discover_tests(heapq_tests)
endif()
