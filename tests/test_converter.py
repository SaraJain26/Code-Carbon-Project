import unittest

from carbon.converter import EnergyUnitConverter
from energy.models import EnergyEstimate


class EnergyUnitConverterTest(unittest.TestCase):

    def setUp(self):

        self.converter = EnergyUnitConverter()

    def test_joules_to_kwh(self):

        energy = EnergyEstimate(
            energy_joules=3_600_000.0,
        )

        kwh = self.converter.joules_to_kwh(
            energy,
        )

        self.assertAlmostEqual(
            kwh,
            1.0,
        )

    def test_zero_energy(self):

        energy = EnergyEstimate(
            energy_joules=0.0,
        )

        kwh = self.converter.joules_to_kwh(
            energy,
        )

        self.assertEqual(
            kwh,
            0.0,
        )

    def test_small_energy(self):

        energy = EnergyEstimate(
            energy_joules=90.0,
        )

        kwh = self.converter.joules_to_kwh(
            energy,
        )

        self.assertAlmostEqual(
            kwh,
            90.0 / 3_600_000.0,
        )


if __name__ == "__main__":
    unittest.main()