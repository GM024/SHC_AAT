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

from shared.experiment_meta import (
    assign_aat_counterbalance,
    assign_iat_version,
    parse_participant_last4,
    smell_condition_order,
    TASK_ORDER_AAT_BLOCK_FIRST,
    TASK_ORDER_IAT_BLOCK_FIRST,
)
from shared.logbook import resolve_participant_assignment


def _task_sequence(task_order_group: str) -> tuple[str, str]:
    if task_order_group == TASK_ORDER_IAT_BLOCK_FIRST:
        return ("IAT", "AAT")
    if task_order_group == TASK_ORDER_AAT_BLOCK_FIRST:
        return ("AAT", "IAT")
    raise ValueError(f"Unsupported task order group: {task_order_group!r}")


def lookup_assignment(participant_last4: str) -> dict[str, str]:
    participant = parse_participant_last4(participant_last4)
    assignment = resolve_participant_assignment(participant.raw_last4)
    smell_sessions = smell_condition_order(assignment.smell_order_group)
    first_task, second_task = _task_sequence(assignment.task_order_group)

    return {
        "participant_id": participant.raw_last4,
        "iat_version": str(assign_iat_version(participant.numeric_id)),
        "aat_counterbalance": assign_aat_counterbalance(participant.numeric_id),
        "task_order_group": assignment.task_order_group,
        "smell_order_group": assignment.smell_order_group,
        "assignment_source": assignment.source,
        "session_1": smell_sessions[0],
        "session_2": smell_sessions[1],
        "session_3": smell_sessions[2],
        "first_task": first_task,
        "second_task": second_task,
    }


def format_assignment_lines(assignment: dict[str, str]) -> list[str]:
    return [
        "Participant assignment",
        f"participant_id={assignment['participant_id']}",
        f"iat_version={assignment['iat_version']}",
        f"aat_counterbalance={assignment['aat_counterbalance']}",
        f"task_order_group={assignment['task_order_group']}",
        f"smell_order_group={assignment['smell_order_group']}",
        f"assignment_source={assignment['assignment_source']}",
        f"first_task={assignment['first_task']}",
        f"second_task={assignment['second_task']}",
        f"session_1={assignment['session_1']}",
        f"session_2={assignment['session_2']}",
        f"session_3={assignment['session_3']}",
    ]


def run(participant_last4: str) -> list[str]:
    return format_assignment_lines(lookup_assignment(participant_last4))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Show the assigned task order, smell order, IAT version, and AAT counterbalance for a participant."
    )
    parser.add_argument("participant_last4", help="Last 4 digits of the participant's phone number.")
    args = parser.parse_args()
    print("\n".join(run(args.participant_last4)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
