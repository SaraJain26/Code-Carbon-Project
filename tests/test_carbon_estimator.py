import unittest

from carbon.estimator import CarbonEstimator


class CarbonEstimatorTest(unittest.TestCase):

    def setUp(self):

        self.estimator = CarbonEstimator()

    def test_carbon_estimation(self):

        carbon = self.estimator.estimate(
            energy_kwh=1.0,
            carbon_intensity=435.0,
        )

        self.assertAlmostEqual(
            carbon.carbon_grams,
            435.0,
        )

    def test_zero_energy(self):

        carbon = self.estimator.estimate(
            energy_kwh=0.0,
            carbon_intensity=435.0,
        )

        self.assertEqual(
            carbon.carbon_grams,
            0.0,
        )

    def test_zero_carbon_intensity(self):

        carbon = self.estimator.estimate(
            energy_kwh=1.0,
            carbon_intensity=0.0,
        )

        self.assertEqual(
            carbon.carbon_grams,
            0.0,
        )

    def test_project_example(self):
        """
        Week 7 example:

        Energy = 90 J

        Energy (kWh) = 90 / 3_600_000

        Carbon = Energy × 435
        """

        energy_kwh = 90.0 / 3_600_000.0

        carbon = self.estimator.estimate(
            energy_kwh=energy_kwh,
            carbon_intensity=435.0,
        )

        expected = energy_kwh * 435.0

        self.assertAlmostEqual(
            carbon.carbon_grams,
            round(expected, 8),
        )


if __name__ == "__main__":
    unittest.main()