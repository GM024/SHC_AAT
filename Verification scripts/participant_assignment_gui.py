from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


VERIFICATION_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = VERIFICATION_DIR.parent
CACHE_DIR = PROJECT_ROOT / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
os.environ["PYTHONPYCACHEPREFIX"] = str(CACHE_DIR)
sys.pycache_prefix = str(CACHE_DIR)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from psychopy import gui

from participant_assignment import format_assignment_lines, lookup_assignment


def _result_lines(assignment: dict[str, str]) -> list[str]:
    return [
        f"Participant ID: {assignment['participant_id']}",
        f"Start with: {assignment['first_task']}",
        f"Then: {assignment['second_task']}",
        f"IAT version: {assignment['iat_version']}",
        f"AAT counterbalance: {assignment['aat_counterbalance']}",
        f"Task order group: {assignment['task_order_group']}",
        f"Smell order group: {assignment['smell_order_group']}",
        f"Session 1: {assignment['session_1']}",
        f"Session 2: {assignment['session_2']}",
        f"Session 3: {assignment['session_3']}",
    ]


def _show_error(message: str) -> None:
    dialog = gui.Dlg(title="Participant Assignment Error")
    dialog.addText(message, color="Red")
    dialog.show()


def show_assignment_gui(initial_last4: str = "") -> int:
    prompt = gui.Dlg(title="Participant Assignment")
    prompt.addText("Enter the last 4 digits of the participant's phone number.")
    prompt.addField("Participant ID (last 4 digits):", initial=initial_last4)
    prompt.show()
    if not prompt.OK:
        return 1

    participant_last4 = str(prompt.data[0]).strip()
    try:
        assignment = lookup_assignment(participant_last4)
    except Exception as exc:
        _show_error(str(exc))
        return 1

    result = gui.Dlg(title=f"Assignment for {assignment['participant_id']}")
    for line in _result_lines(assignment):
        result.addText(line)
    result.addText("")
    result.addText("Run the practice script first for the starting task.")
    result.show()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Show a simple GUI for participant assignment lookup."
    )
    parser.add_argument(
        "--participant-last4",
        default="",
        help="Optional participant ID to prefill or use for non-interactive output.",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print the resolved assignment instead of opening the GUI.",
    )
    args = parser.parse_args()

    if args.stdout:
        if not args.participant_last4:
            raise SystemExit("--stdout requires --participant-last4.")
        print("\n".join(format_assignment_lines(lookup_assignment(args.participant_last4))))
        return 0

    return show_assignment_gui(args.participant_last4)


if __name__ == "__main__":
    raise SystemExit(main())
