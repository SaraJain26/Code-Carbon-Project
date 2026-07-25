import unittest
from unittest.mock import patch

from hardware_profile.profiler import HardwareProfiler


class HardwareProfilerTest(unittest.TestCase):

    @patch("hardware_profile.profiler.detect_gpu")
    @patch("hardware_profile.profiler.psutil.virtual_memory")
    @patch("hardware_profile.profiler.psutil.cpu_freq")
    @patch("hardware_profile.profiler.psutil.cpu_count")
    @patch("hardware_profile.profiler.platform.machine")
    @patch("hardware_profile.profiler.platform.system")
    @patch("hardware_profile.profiler.platform.processor")
    @patch("hardware_profile.profiler.platform.platform")
    @patch("hardware_profile.profiler.platform.python_version")
    def test_profile(
        self,
        mock_python_version,
        mock_platform,
        mock_processor,
        mock_system,
        mock_machine,
        mock_cpu_count,
        mock_cpu_freq,
        mock_virtual_memory,
        mock_detect_gpu,
    ):
        mock_processor.return_value = "Intel Core i7-13620H"

        mock_system.return_value = "Windows"

        mock_machine.return_value = "AMD64"

        mock_cpu_count.side_effect = [10, 16]

        mock_cpu_freq.return_value = type(
            "Freq",
            (),
            {"max": 4900},
        )

        mock_virtual_memory.return_value = type(
            "Memory",
            (),
            {"total": 16 * (1024 ** 3)},
        )

        mock_detect_gpu.return_value = (
            True,
            "NVIDIA RTX 4060",
        )

        mock_python_version.return_value = "3.11"

        mock_platform.return_value = "Windows"

        profiler = HardwareProfiler()

        profile = profiler.profile()

        self.assertEqual(profile.cpu_vendor, "Intel")
        self.assertEqual(profile.physical_cores, 10)
        self.assertEqual(profile.logical_threads, 16)
        self.assertAlmostEqual(profile.cpu_frequency_ghz, 4.9)
        self.assertEqual(profile.ram_gb, 16)
        self.assertTrue(profile.gpu_present)


if __name__ == "__main__":
    unittest.main()