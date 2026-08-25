import sys
from pathlib import Path

# Add 'src' folder to sys.path to allow resolving modules like carbon, pipeline, etc.
# We append it to the end of sys.path to prevent it from shadowing the root-level 'api' package.
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

from src.api.main import app