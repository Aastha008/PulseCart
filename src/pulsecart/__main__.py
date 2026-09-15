"""
PulseCart Main Kedro Entrypoint.
Allows running the pipeline via `python -m pulsecart` or programmatically.
"""

import sys
from pathlib import Path
from kedro.framework.project import configure_project
from kedro.framework.session import KedroSession

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PACKAGE_NAME = "pulsecart"


def main():
    """Executes the Kedro pipeline session."""
    if str(PROJECT_ROOT / "src") not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT / "src"))
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    configure_project(PACKAGE_NAME)
    with KedroSession.create(project_path=PROJECT_ROOT) as session:
        session.run()


if __name__ == "__main__":
    main()
