import os
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
CACHE_DIR = PROJECT_ROOT / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
os.environ["PYTHONPYCACHEPREFIX"] = str(CACHE_DIR)
sys.pycache_prefix = str(CACHE_DIR)

from iat_core import run_iat

from shared.experiment_meta import SCRIPT_TYPE_MAIN


if __name__ == "__main__":
    run_iat(SCRIPT_TYPE_MAIN)
