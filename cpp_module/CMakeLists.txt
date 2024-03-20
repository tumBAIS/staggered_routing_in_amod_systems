cmake_minimum_required(VERSION 3.16 FATAL_ERROR)
set(CMAKE_CXX_STANDARD 17)
project(cpp_module)

find_package(Python COMPONENTS Interpreter Development REQUIRED)
message(STATUS "Found python binary: ${Python_EXECUTABLE} (Version ${Python_VERSION})")

set(PYBIND11_PYTHON_VERSION ${Python_VERSION})
set(PYTHON_EXECUTABLE ${Python_EXECUTABLE})
set(PYTHON_LIBS ${Python_LIBS})


add_subdirectory(lib/pybind11)

add_library(project_options INTERFACE)
target_compile_features(project_options INTERFACE cxx_std_17)

# enable ipo/lto for non-debug builds and all targets
include(CheckIPOSupported)
check_ipo_supported(RESULT is_ipo_supported)
if (is_ipo_supported)
    set(CMAKE_INTERPROCEDURAL_OPTIMIZATION TRUE)
endif ()
set(CMAKE_INTERPROCEDURAL_OPTIMIZATION_DEBUG FALSE)

file(GLOB_RECURSE SOURCES "src/*.cpp")

# test target - we need to create a lib with static bindings for testing with catch2
pybind11_add_module(${PROJECT_NAME}_catch2 STATIC ${SOURCES})
target_include_directories(${PROJECT_NAME}_catch2 PRIVATE include)
target_link_libraries(${PROJECT_NAME}_catch2 PRIVATE project_options)
add_subdirectory(catch2_tests)

# python module target
pybind11_add_module(${PROJECT_NAME} ${SOURCES})
target_include_directories(${PROJECT_NAME} PRIVATE include)
target_link_libraries(${PROJECT_NAME} PRIVATE project_options)