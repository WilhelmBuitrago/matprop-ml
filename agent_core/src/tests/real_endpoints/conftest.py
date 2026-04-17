import sys
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

from conftest_real import *  # noqa: F401,F403
from conftest_report import *  # noqa: F401,F403
