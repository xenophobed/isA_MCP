"""
Root conftest for isA_MCP tests.

This file ensures the project root is in sys.path for proper imports.
"""
import sys
from pathlib import Path

# Add project root to sys.path before any imports - this MUST happen first
PROJECT_ROOT = Path(__file__).parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def pytest_configure(config):
    """Configure pytest at startup."""
    # Ensure project root is in path
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
