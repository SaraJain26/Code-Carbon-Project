import unittest

from energy.models import (
    RuntimeEstimate,
    EnergyEstimate,
    EnergyResult,
)


class EnergyModelsTest(unittest.TestCase):

    def test_runtime_creation(self):

        runtime = RuntimeEstimate(
            runtime=1.25,
        )

        self.assertEqual(
            runtime.runtime,
            1.25,
        )

    def test_energy_creation(self):

        energy = EnergyEstimate(
            energy_joules=52.4,
        )

        self.assertEqual(
            energy.energy_joules,
            52.4,
        )

    def test_energy_result_creation(self):

        runtime = RuntimeEstimate(
            runtime=1.25,
        )

        energy = EnergyEstimate(
            energy_joules=52.4,
        )

        result = EnergyResult(
            runtime=runtime,
            energy=energy,
        )

        self.assertEqual(
            result.runtime.runtime,
            1.25,
        )

        self.assertEqual(
            result.energy.energy_joules,
            52.4,
        )


if __name__ == "__main__":
    unittest.main()