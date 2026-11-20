import os
import sys

from config import EXTERNAL_DIR

_EXTERNAL_LIBS_IMPORTED = False


def import_external_libs() -> None:
    global _EXTERNAL_LIBS_IMPORTED
    if _EXTERNAL_LIBS_IMPORTED:
        return

    _EXTERNAL_LIBS_IMPORTED = True

    match sys.platform:
        case "win32":
            dir_path = str(EXTERNAL_DIR / "windows")
            os.add_dll_directory(dir_path)
            os.environ["PATH"] = dir_path + os.pathsep + os.environ["PATH"]

        case "linux":
            import ctypes

            ctypes.CDLL(
                str(EXTERNAL_DIR / "linux" / "libopus.so"), mode=ctypes.RTLD_GLOBAL
            )

        case "darwin":
            import ctypes

            ctypes.CDLL(str(EXTERNAL_DIR / "macos" / "libopus.dylib"))

        case platform:
            raise OSError(f"Unsupported platform: {platform}")
