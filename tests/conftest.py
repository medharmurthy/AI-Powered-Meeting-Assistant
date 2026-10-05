import os
from pathlib import Path
import sys
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Ensure tests use the project config.yaml
os.environ["VERBATIM_CONFIG"] = str(REPO_ROOT / "config.yaml")
