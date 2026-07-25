"""
GPU detection utilities.

This module performs lightweight cross-platform GPU detection
without introducing additional dependencies.

Detection priority:

Windows:
    1. PowerShell (Get-CimInstance)
    2. WMIC

Linux:
    lspci

macOS:
    system_profiler
"""

from __future__ import annotations

import platform
import subprocess


def detect_gpu() -> tuple[bool, str | None]:
    """
    Detect whether a GPU is available.

    Returns
    -------
    tuple
        (gpu_present, gpu_name)
    """

    system = platform.system()

    if system == "Windows":
        return _detect_windows_gpu()

    if system == "Linux":
        return _detect_linux_gpu()

    if system == "Darwin":
        return _detect_macos_gpu()

    return False, None


def _detect_windows_gpu() -> tuple[bool, str | None]:
    """
    Detect GPU on Windows.

    Tries PowerShell first, then falls back to WMIC.
    """

    # --------------------------
    # PowerShell (preferred)
    # --------------------------

    try:
        result = subprocess.run(
            [
                "powershell",
                "-Command",
                "(Get-CimInstance Win32_VideoController).Name",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        lines = [
            line.strip()
            for line in result.stdout.splitlines()
            if line.strip()
        ]

        if lines:
            return True, lines[0]

    except Exception:
        pass

    # --------------------------
    # WMIC fallback
    # --------------------------

    try:
        result = subprocess.run(
            [
                "wmic",
                "path",
                "win32_VideoController",
                "get",
                "name",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        lines = [
            line.strip()
            for line in result.stdout.splitlines()
            if line.strip()
            and line.strip().lower() != "name"
        ]

        if lines:
            return True, lines[0]

    except Exception:
        pass

    return False, None


def _detect_linux_gpu() -> tuple[bool, str | None]:
    """
    Detect GPU using lspci.
    """

    try:
        result = subprocess.run(
            ["lspci"],
            capture_output=True,
            text=True,
            check=True,
        )

        for line in result.stdout.splitlines():

            lower = line.lower()

            if (
                "vga" in lower
                or "3d controller" in lower
                or "display controller" in lower
            ):
                return True, line.strip()

    except Exception:
        pass

    return False, None


def _detect_macos_gpu() -> tuple[bool, str | None]:
    """
    Detect GPU on macOS.
    """

    try:
        result = subprocess.run(
            [
                "system_profiler",
                "SPDisplaysDataType",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        for line in result.stdout.splitlines():

            line = line.strip()

            if line.startswith("Chipset Model:"):
                return (
                    True,
                    line.replace(
                        "Chipset Model:",
                        "",
                    ).strip(),
                )

    except Exception:
        pass

    return False, None