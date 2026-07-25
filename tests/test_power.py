import unittest

from hardware_profile.power import ReferencePowerEstimator


class ReferencePowerEstimatorTest(unittest.TestCase):

    def setUp(self):
        self.estimator = ReferencePowerEstimator()

    def test_intel_h_series(self):
        power = self.estimator.estimate(
            "Intel",
            "Intel Core i7-13620H",
        )

        self.assertEqual(power, 45.0)

    def test_intel_u_series(self):
        power = self.estimator.estimate(
            "Intel",
            "Intel Core i7-1355U",
        )

        self.assertEqual(power, 15.0)

    def test_intel_hx_series(self):
        power = self.estimator.estimate(
            "Intel",
            "Intel Core i9-14900HX",
        )

        self.assertEqual(power, 55.0)

    def test_intel_core_ultra(self):
        power = self.estimator.estimate(
            "Intel",
            "Intel Core Ultra 7 155H",
        )

        self.assertEqual(power, 45.0)

    def test_amd_hs_series(self):
        power = self.estimator.estimate(
            "AMD",
            "AMD Ryzen 7 7840HS",
        )

        self.assertEqual(power, 35.0)

    def test_amd_hx_series(self):
        power = self.estimator.estimate(
            "AMD",
            "AMD Ryzen 9 7945HX",
        )

        self.assertEqual(power, 55.0)

    def test_amd_ryzen_ai(self):
        power = self.estimator.estimate(
            "AMD",
            "AMD Ryzen AI 9 HX370",
        )

        self.assertEqual(power, 55.0)

    def test_apple(self):
        power = self.estimator.estimate(
            "Apple",
            "Apple M3",
        )

        self.assertEqual(power, 22.0)

    def test_unknown_processor(self):
        power = self.estimator.estimate(
            "Unknown",
            "MyCPU 1234",
        )

        self.assertEqual(power, 45.0)


if __name__ == "__main__":
    unittest.main()