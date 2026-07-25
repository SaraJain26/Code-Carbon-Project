"""
Hardware profiler.

Collects hardware information from the host system without requiring
administrator privileges or external services.

The profiler gathers:

- CPU model
- CPU vendor
- Physical cores
- Logical threads
- CPU frequency
- Installed RAM
- Operating system
- Machine architecture
- GPU information

The collected information is returned as a HardwareProfile object.
"""

from __future__ import annotations

import platform
import subprocess

import psutil

from .gpu import detect_gpu
from .models import HardwareProfile


class HardwareProfiler:
    """
    Profiles the host machine.
    """

    def profile(self) -> HardwareProfile:
        """
        Collect hardware information.

        Returns
        -------
        HardwareProfile
            Raw hardware profile.
        """

        cpu_model = self._detect_cpu_model()

        cpu_vendor = self._detect_vendor(cpu_model)

        physical_cores = psutil.cpu_count(logical=False) or 1
        logical_threads = psutil.cpu_count(logical=True) or physical_cores

        frequency = psutil.cpu_freq()

        cpu_frequency_ghz = 0.0

        if frequency is not None:
            cpu_frequency_ghz = round(frequency.max / 1000.0, 2)

        ram_gb = round(
            psutil.virtual_memory().total / (1024 ** 3),
            2,
        )

        operating_system = platform.system()

        architecture = platform.machine()

        gpu_present, gpu_model = detect_gpu()

        return HardwareProfile(
            cpu_model=cpu_model,
            cpu_vendor=cpu_vendor,
            physical_cores=physical_cores,
            logical_threads=logical_threads,
            cpu_frequency_ghz=cpu_frequency_ghz,
            ram_gb=ram_gb,
            operating_system=operating_system,
            architecture=architecture,
            gpu_present=gpu_present,
            gpu_model=gpu_model,
            metadata={
                "python_version": platform.python_version(),
                "platform": platform.platform(),
            },
        )

    @staticmethod
    def _detect_cpu_model() -> str:
        """
        Detect CPU model using platform-specific mechanisms.

        Detection order:

        1. PowerShell (Windows)
        2. WMIC (Windows)
        3. platform.processor()
        """

        if platform.system() == "Windows":

            try:
                result = subprocess.run(
                    [
                        "powershell",
                        "-Command",
                        "(Get-CimInstance Win32_Processor).Name",
                    ],
                    capture_output=True,
                    text=True,
                    check=True,
                )

                name = result.stdout.strip()

                if name:
                    return name

            except Exception:
                pass

            try:
                result = subprocess.run(
                    [
                        "wmic",
                        "cpu",
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
                    if line.strip() and line.strip().lower() != "name"
                ]

                if lines:
                    return lines[0]

            except Exception:
                pass

        cpu = platform.processor().strip()

        if cpu:
            return cpu

        return "Unknown"

    @staticmethod
    def _detect_vendor(cpu_model: str) -> str:
        """
        Detect CPU vendor from processor string.
        """

        name = cpu_model.lower()

        if "intel" in name:
            return "Intel"

        if "amd" in name or "ryzen" in name:
            return "AMD"

        if (
            "apple" in name
            or "m1" in name
            or "m2" in name
            or "m3" in name
            or "m4" in name
        ):
            return "Apple"

        if (
            "qualcomm" in name
            or "snapdragon" in name
        ):
            return "Qualcomm"

        return "Unknown"