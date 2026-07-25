import unittest
from unittest.mock import patch

from hardware_profile.engine import HardwareProfilingEngine
from hardware_profile.models import (
    HardwareProfile,
    HardwareScore,
    NormalizedHardwareProfile,
)


class HardwareEngineTest(unittest.TestCase):

    @patch("hardware_profile.engine.ReferencePowerEstimator")
    @patch("hardware_profile.engine.HardwareNormalizer")
    @patch("hardware_profile.engine.HardwareProfiler")
    def test_analysis_pipeline(
        self,
        mock_profiler_cls,
        mock_normalizer_cls,
        mock_power_cls,
    ):
        profile = HardwareProfile(
            cpu_model="Intel Core i7",
            cpu_vendor="Intel",
            physical_cores=16,
            logical_threads=24,
            cpu_frequency_ghz=4.5,
            ram_gb=32,
            operating_system="Windows",
            architecture="AMD64",
            gpu_present=True,
        )

        normalized = NormalizedHardwareProfile(
            core_score=0.5,
            frequency_score=0.9,
            ram_score=0.5,
            gpu_score=1.0,
        )

        score = HardwareScore(
            hardware_performance_index=0.725,
            reference_compute_power_w=45.0,
        )

        profiler = mock_profiler_cls.return_value
        profiler.profile.return_value = profile

        normalizer = mock_normalizer_cls.return_value
        normalizer.normalize.return_value = normalized
        normalizer.compute_hardware_score.return_value = score

        estimator = mock_power_cls.return_value
        estimator.estimate.return_value = 45.0

        engine = HardwareProfilingEngine()

        result = engine.analyze()

        self.assertEqual(result[0], profile)
        self.assertEqual(result[1], normalized)
        self.assertEqual(result[2], score)


if __name__ == "__main__":
    unittest.main()