import unittest

from detector.rules.filter import DetectorFilter
from detector import DetectionContext


class DetectorFilterTest(unittest.TestCase):

    def test_filter_allows_everything_by_default(self):

        detector_filter = DetectorFilter()

        self.assertTrue(
            detector_filter.allows(
                "EKB-NET-001",
                None,  # context unused for now
            )
        )


if __name__ == "__main__":
    unittest.main()