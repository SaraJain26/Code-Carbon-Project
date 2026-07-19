from detector.context import DetectionContext
from detector.interfaces import CandidateExtractor
from detector.models import Candidate

from detector.rules import DetectorRegistry


class DefaultCandidateExtractor(CandidateExtractor):
    """
    Delegates candidate extraction to the built-in detector registry.
    """

    def __init__(self) -> None:
        self._registry = DetectorRegistry()

    def extract(
        self,
        context: DetectionContext,
    ) -> list[Candidate]:
        return self._registry.detect(context)