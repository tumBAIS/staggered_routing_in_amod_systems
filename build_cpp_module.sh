#!/bin/bash

# Unload and load required modules
module unload python
module load python/3.11.9
module load cmake

# Remove build directories if they exist
if [ -d "cpp_module/cmake-build-release" ]; then
    rm -rf cpp_module/cmake-build-release
fi

if [ -d "kspwlo/cmake-build-release" ]; then
    rm -rf kspwlo/cmake-build-release
fi

# Create CMake files using the correct interpreter and build type
cmake -S cpp_module/ -B cpp_module/cmake-build-release -DCMAKE_BUILD_TYPE=Release
cmake -S kspwlo/ -B kspwlo/cmake-build-release -DCMAKE_BUILD_TYPE=Release

# Build CPP module
cmake --build cpp_module/cmake-build-release --target cpp_module
cmake --build kspwlo/cmake-build-release --target kspwlo
