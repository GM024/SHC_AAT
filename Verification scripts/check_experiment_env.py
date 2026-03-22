from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path


VERIFICATION_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = VERIFICATION_DIR.parent
CACHE_DIR = PROJECT_ROOT / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
os.environ["PYTHONPYCACHEPREFIX"] = str(CACHE_DIR)
sys.pycache_prefix = str(CACHE_DIR)
IAT_DIR = PROJECT_ROOT / "Implicit Association Task" / "IAT Task Script"
AAT_DIR = PROJECT_ROOT / "Approach Avoidance Task" / "AAT Task Script"
for path in (PROJECT_ROOT, IAT_DIR, AAT_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import aat_core
import iat_core
from shared.experiment_meta import get_logbook_path
from shared.logbook import ensure_logbook_template


def check_module(module_name: str) -> tuple[bool, str]:
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError:
        return False, f"{module_name}=missing"
    version = getattr(module, "__version__", "unknown")
    return True, f"{module_name}={version}"


def check_logbook() -> tuple[bool, list[str]]:
    logbook_path = get_logbook_path()
    try:
        created_path = ensure_logbook_template(logbook_path)
    except Exception as exc:
        return False, [f"logbook=failed ({type(exc).__name__}: {exc})"]
    if not created_path.exists():
        return False, [f"logbook=missing ({created_path})"]
    if not created_path.parent.exists():
        return False, [f"logbook_dir=missing ({created_path.parent})"]
    return True, [
        f"logbook={created_path}",
        f"logbook_dir_writable={created_path.parent}",
    ]


def check_iat_assets() -> tuple[bool, list[str]]:
    try:
        stimulus_pools = iat_core.load_stimulus_pools()
    except Exception as exc:
        return False, [f"iat_assets=failed ({type(exc).__name__}: {exc})"]
    return True, [
        f"iat_shc={len(stimulus_pools[iat_core.CAT_SHC])}",
        f"iat_disease={len(stimulus_pools[iat_core.CAT_DISEASE])}",
        f"iat_danger={len(stimulus_pools[iat_core.CAT_DANGER])}",
    ]


def check_aat_assets() -> tuple[bool, list[str]]:
    try:
        stimuli = aat_core.discover_stimuli(aat_core.SHC_IMAGE_DIR, aat_core.FHC_IMAGE_DIR)
    except Exception as exc:
        return False, [f"aat_assets=failed ({type(exc).__name__}: {exc})"]
    shc_count = sum(1 for stimulus in stimuli if stimulus["category"] == "SHC")
    fhc_count = sum(1 for stimulus in stimuli if stimulus["category"] == "FHC")
    return True, [
        f"aat_shc={shc_count}",
        f"aat_fhc={fhc_count}",
    ]


def run_checks() -> tuple[list[str], list[str]]:
    lines = ["Experiment environment check"]
    errors: list[str] = []
    lines.append(f"python={sys.version.split()[0]}")

    for module_name in ("psychopy", "openpyxl"):
        ok, line = check_module(module_name)
        lines.append(line)
        if not ok:
            errors.append(line)

    for check in (check_logbook, check_iat_assets, check_aat_assets):
        ok, check_lines = check()
        lines.extend(check_lines)
        if not ok:
            errors.extend(check_lines)

    if errors:
        lines.append("Environment check failed.")
    else:
        lines.append("Environment check passed.")
    return lines, errors


def main() -> int:
    lines, errors = run_checks()
    stream = sys.stderr if errors else sys.stdout
    print("\n".join(lines), file=stream)
    if errors:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
