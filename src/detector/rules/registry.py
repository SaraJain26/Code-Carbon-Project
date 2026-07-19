from detector.context import DetectionContext
from detector.models import Candidate

from .filter import DetectorFilter
from .async_operations import AsyncOperationDetector
from .file_operations import FileOperationDetector
from .nested_loops import NestedLoopDetector
from .network_calls import NetworkCallDetector
from .recursive_computation import RecursiveComputationDetector


class DetectorRegistry:
    """
    Registry responsible for executing every built-in detector.

    A DetectorFilter is consulted before invoking each detector so
    detectors can later be enabled/disabled without modifying the
    registry implementation.
    """

    def __init__(self) -> None:
        self._filter = DetectorFilter()

        self._detectors = [
            NestedLoopDetector(),
            RecursiveComputationDetector(),
            NetworkCallDetector(),
            FileOperationDetector(),
            AsyncOperationDetector(),
        ]

    @property
    def detectors(self):
        return tuple(self._detectors)

    def detect(
        self,
        context: DetectionContext,
    ) -> list[Candidate]:

        candidates: list[Candidate] = []

        for detector in self._detectors:

            if not self._filter.allows(
                detector.RULE_ID,
                context,
            ):
                continue

            candidates.extend(detector.detect(context))

        return candidates