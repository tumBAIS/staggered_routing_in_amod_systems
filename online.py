#!/usr/bin/env python3.9
from runProcedure import runProcedure


def main(inputSource: str) -> None:
    if inputSource not in ["script", "console"]:
        raise RuntimeError("please specify correct input method: script or console")
    runProcedure(inputSource)


if __name__ == "__main__":
    main(inputSource="script")
