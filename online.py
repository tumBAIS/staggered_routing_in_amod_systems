#!/usr/bin/env python3.9
import sys
from pathlib import Path

path_to_repo = Path(__file__).parent
path_to_src = path_to_repo / "src"

sys.path.append(path_to_repo.as_posix())
sys.path.append(path_to_src.as_posix())

# C++
build = "relwithdebinfo"  # release, debug, relwithdebinfo
print("\n" + "=" * 60)
print(f"{'C++ BUILD:':^20} {build.upper():^40}")
print("=" * 60 + "\n")

path_to_build = path_to_repo / f"cpp_module/cmake-build-{build}"
sys.path.append(path_to_build.as_posix())

from runProcedure import runProcedure


def main(inputSource: str) -> None:
    if inputSource not in ["script", "console"]:
        raise RuntimeError("please specify correct input method: script or console")
    runProcedure(inputSource)


if __name__ == "__main__":
    main(inputSource="script")
