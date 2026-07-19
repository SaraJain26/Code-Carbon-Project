"""File processing benchmark."""

from pathlib import Path
import os


def copy_lines(source: str, destination: str) -> int:
    count = 0
    with open(source, "r", encoding="utf-8") as reader:
        with open(destination, "w", encoding="utf-8") as writer:
            for line in reader:
                writer.write(line.strip() + "\n")
                count += 1
    return count


def load_config(path: Path) -> str:
    if os.path.exists(path):
        return path.read_text(encoding="utf-8")
    return ""
