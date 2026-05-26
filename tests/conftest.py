import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Disable rate limits and use test env for the whole suite.
os.environ.setdefault("REALITY_CHECK_ENV", "test")
