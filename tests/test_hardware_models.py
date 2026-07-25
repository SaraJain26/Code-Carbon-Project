import unittest

from hardware_profile.models import (
    HardwareProfile,
    HardwareScore,
    NormalizedHardwareProfile,
)


class HardwareModelsTest(unittest.TestCase):

    def test_hardware_profile_creation(self):
        profile = HardwareProfile(
            cpu_model="Intel Core i7-13620H",
            cpu_vendor="Intel",
            physical_cores=10,
            logical_threads=16,
            cpu_frequency_ghz=4.9,
            ram_gb=16,
            operating_system="Windows",
            architecture="AMD64",
            gpu_present=True,
            gpu_model="NVIDIA RTX 4060",
        )

        self.assertEqual(profile.cpu_model, "Intel Core i7-13620H")
        self.assertEqual(profile.cpu_vendor, "Intel")
        self.assertEqual(profile.physical_cores, 10)
        self.assertEqual(profile.logical_threads, 16)
        self.assertTrue(profile.gpu_present)

    def test_normalized_profile_creation(self):
        normalized = NormalizedHardwareProfile(
            core_score=0.50,
            frequency_score=0.98,
            ram_score=0.25,
            gpu_score=1.00,
        )

        self.assertEqual(normalized.core_score, 0.50)
        self.assertEqual(normalized.frequency_score, 0.98)
        self.assertEqual(normalized.ram_score, 0.25)
        self.assertEqual(normalized.gpu_score, 1.00)

    def test_hardware_score_creation(self):
        score = HardwareScore(
            hardware_performance_index=0.6825,
            reference_compute_power_w=45.0,
        )

        self.assertEqual(score.hardware_performance_index, 0.6825)
        self.assertEqual(score.reference_compute_power_w, 45.0)


if __name__ == "__main__":
    unittest.main()