#!/usr/bin/env python3.9
import sys
from pathlib import Path


def setup_paths():
    # Define paths relative to the script location
    path_to_repo = Path(__file__).resolve().parent
    path_to_src = path_to_repo / "src"
    path_to_build = path_to_repo / "cpp_module/cmake-build-{}".format(build)

    # Append paths to the system path for module discovery
    sys.path.extend([path_to_repo.as_posix(), path_to_src.as_posix(), path_to_build.as_posix()])


def display_build_configuration(build_type):
    # Display the current C++ build configuration
    print("\n" + "=" * 60)
    print(f"{'C++ BUILD:':^20} {build_type.upper():^40}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    # Configuration for C++ build (options: release, debug, relwithdebinfo)
    build = "relwithdebinfo"

    # Setup paths for module imports
    setup_paths()

    # Display build configuration
    display_build_configuration(build)

    # Import and run the procedure from the utils package
    from utils.run_procedure import run_procedure

    run_procedure(source="script")
