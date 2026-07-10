"""Pytest configuration for MBOS tests."""
import sys
from pathlib import Path

# Ensure app/ is importable from tests/
sys.path.insert(0, str(Path(__file__).parent.parent))
