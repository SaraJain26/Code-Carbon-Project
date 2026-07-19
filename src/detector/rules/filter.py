from detector.context import DetectionContext


class DetectorFilter:
    """
    Determines whether a detector should execute.
    """

    def allows(
        self,
        rule_id: str,
        context: DetectionContext,
    ) -> bool:
        return True