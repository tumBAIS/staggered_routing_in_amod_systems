cmake_minimum_required(VERSION 3.16 FATAL_ERROR)
set(CMAKE_CXX_STANDARD 20)
project(cpp_module)

# Find and configure Python
find_package(Python 3.11.9 EXACT COMPONENTS Interpreter Development REQUIRED)
message(STATUS "Found python binary: ${Python_EXECUTABLE} (Version ${Python_VERSION})")

set(PYBIND11_PYTHON_VERSION ${Python_VERSION})
set(PYTHON_EXECUTABLE ${Python_EXECUTABLE})
set(PYTHON_LIBS ${Python_LIBS})

# Add pybind11 subdirectory
add_subdirectory(lib/pybind11)

# Create an interface library for project options
add_library(project_options INTERFACE)
target_compile_features(project_options INTERFACE cxx_std_20)

# Enable IPO/LTO for non-debug builds and all targets
include(CheckIPOSupported)
check_ipo_supported(RESULT is_ipo_supported)
if (is_ipo_supported)
    set(CMAKE_INTERPROCEDURAL_OPTIMIZATION TRUE)
endif ()
set(CMAKE_INTERPROCEDURAL_OPTIMIZATION_DEBUG FALSE)

# Add source files
file(GLOB_RECURSE SOURCES "src/*.cpp")

# Test target - we need to create a lib with static bindings for testing with catch2
pybind11_add_module(${PROJECT_NAME}_catch2 STATIC ${SOURCES})
target_include_directories(${PROJECT_NAME}_catch2 PRIVATE include)
add_subdirectory(catch2_tests)

# Python module target
pybind11_add_module(${PROJECT_NAME} ${SOURCES})
target_include_directories(${PROJECT_NAME} PRIVATE include)
