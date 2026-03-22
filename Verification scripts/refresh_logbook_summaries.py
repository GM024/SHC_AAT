from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = PROJECT_ROOT / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
os.environ["PYTHONPYCACHEPREFIX"] = str(CACHE_DIR)
sys.pycache_prefix = str(CACHE_DIR)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.logbook import refresh_balance_summaries


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh IAT/AAT balance summaries in the MRP logbook.")
    parser.add_argument(
        "--logbook",
        type=Path,
        default=None,
        help="Path to the workbook. Defaults to the canonical MRP logbook.",
    )
    args = parser.parse_args()

    path = refresh_balance_summaries(args.logbook)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
