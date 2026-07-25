import unittest

from hardware_profile.models import HardwareProfile
from hardware_profile.normalizer import HardwareNormalizer


class HardwareNormalizerTest(unittest.TestCase):

    def setUp(self):
        self.normalizer = HardwareNormalizer()

    def test_normalization(self):
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

        normalized = self.normalizer.normalize(profile)

        self.assertAlmostEqual(normalized.core_score, 0.5)
        self.assertAlmostEqual(normalized.frequency_score, 0.9)
        self.assertAlmostEqual(normalized.ram_score, 0.5)
        self.assertEqual(normalized.gpu_score, 1.0)

    def test_hpi_computation(self):
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

        normalized = self.normalizer.normalize(profile)

        score = self.normalizer.compute_hardware_score(
            normalized,
            45.0,
        )

        expected = (
            0.5 +
            0.9 +
            0.5 +
            1.0
        ) / 4

        self.assertAlmostEqual(
            score.hardware_performance_index,
            expected,
            places=4,
        )

        self.assertEqual(score.reference_compute_power_w, 45.0)


if __name__ == "__main__":
    unittest.main()