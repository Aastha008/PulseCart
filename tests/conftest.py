"""
PulseCart Root Pytest Configuration
Registers global markers and sys.path adjustments.
"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def pytest_configure(config):
    """Register custom markers for PulseCart."""
    config.addinivalue_line("markers", "tier1: Tier 1 - Feature Coverage tests")
    config.addinivalue_line("markers", "tier2: Tier 2 - Boundary & Corner Case tests")
    config.addinivalue_line("markers", "tier3: Tier 3 - Cross-Feature Combination tests")
    config.addinivalue_line("markers", "tier4: Tier 4 - Real-World Application Scenario tests")
    config.addinivalue_line("markers", "feature(name): Feature identifier under test")
