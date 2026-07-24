import tempfile
import textwrap
import unittest
from pathlib import Path

from complexity.radon_adapter import RadonAdapter


class RadonAdapterTest(unittest.TestCase):

    def setUp(self):
        self.adapter = RadonAdapter()

    def test_compute_simple_function(self):

        code = textwrap.dedent(
            """
            def add(a, b):
                return a + b
            """
        )

        with tempfile.TemporaryDirectory() as directory:

            source = Path(directory) / "sample.py"

            source.write_text(code, encoding="utf-8")

            complexity = self.adapter.compute(source)

            self.assertEqual(complexity, 1.0)

    def test_compute_branching_function(self):

        code = textwrap.dedent(
            """
            def classify(x):

                if x > 0:
                    return "positive"

                elif x < 0:
                    return "negative"

                return "zero"
            """
        )

        with tempfile.TemporaryDirectory() as directory:

            source = Path(directory) / "sample.py"

            source.write_text(code, encoding="utf-8")

            complexity = self.adapter.compute(source)

            self.assertGreater(complexity, 1.0)


if __name__ == "__main__":
    unittest.main()