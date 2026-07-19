"""Classes, inheritance, and exceptions benchmark."""


class ProcessingError(Exception):
    pass


class Processor:
    batch_size = 100

    def __init__(self, name: str) -> None:
        self.name = name

    def process(self, values: list[int]) -> int:
        try:
            if not values:
                raise ProcessingError("empty input")
            return sum(values)
        except ProcessingError:
            return 0
        finally:
            self.name = self.name.strip()


class StreamingProcessor(Processor):
    async def process_async(self, values: list[int]) -> int:
        total = 0
        for value in values:
            total += value
        return total
