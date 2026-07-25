import unittest

from energy.estimator import EnergyEstimator
from energy.models import RuntimeEstimate
from hardware_profile.models import HardwareScore


class EnergyEstimatorTest(unittest.TestCase):

    def setUp(self):
        self.estimator = EnergyEstimator()

    def test_energy(self):

        runtime = RuntimeEstimate(
            runtime=2.0,
        )

        hardware = HardwareScore(
            hardware_performance_index=0.40,
            reference_compute_power_w=45.0,
        )

        energy = self.estimator.estimate(
            runtime,
            hardware,
        )

        self.assertEqual(
            energy.energy_joules,
            90.0,
        )


if __name__ == "__main__":
    unittest.main()