# C++ Module for Staggered Routing AMoD Systems

This module provides the computational core for the staggered routing problem in Autonomous Mobility-on-Demand (AMoD) systems. It integrates with Python through `pybind11` and uses `catch2` for testing.

## Dependencies

The module relies on external libraries for its operation:

- **pybind11**: A lightweight header-only library that enables the creation of Python bindings for C++ code.
- **catch2 (v2.x)**: A multi-paradigm test framework for C++, which is used for unit testing in this project.

### Setting Up External Libraries

#### pybind11

To ensure compatibility and ease of setup, `pybind11` version 2.13.6 is included directly via git. To install this 
specific version, from the cpp_module directory run the following command:
   ```bash
    Invoke-WebRequest -Uri "https://github.com/pybind/pybind11/archive/refs/tags/v2.13.6.zip" -OutFile "pybind11-v2.13.6.zip"
    Expand-Archive -Path "pybind11-v2.13.6.zip" -DestinationPath "lib"
    Remove-Item -Path "lib/pybind11-v2.13.6.zip"

   ```
Rename the extracted directory to 'pybind11'
```bash
    Rename-Item -Path "lib\pybind11-2.13.6" -NewName "pybind11"
```

## Building the Module

After setting up the external libraries, you're ready to build the C++ module. 
The build process compiles the C++ code and generates the necessary bindings for Python integration. 


### To add or modify build configurations (for CLion):
- Go to File > Settings (on Windows/Linux) or CLion > Preferences (on macOS).
- Navigate to Build, Execution, Deployment > CMake.
- Here, you can add a new profile by clicking the + button and setting the build type to Release (or any other configuration you need).

