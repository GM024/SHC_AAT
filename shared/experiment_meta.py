from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


TASK_IAT = "IAT"
TASK_AAT = "AAT"
VALID_TASKS = {TASK_IAT, TASK_AAT}

SCRIPT_TYPE_PRACTICE = "practice"
SCRIPT_TYPE_MAIN = "main"
VALID_SCRIPT_TYPES = {SCRIPT_TYPE_PRACTICE, SCRIPT_TYPE_MAIN}

CONDITION_CONTROL_NO_SMELL = "control_no_smell"
CONDITION_CLEAN_ODOUR = "clean_odour"
CONDITION_ISOVALERIC_ACID = "isovaleric_acid"
VALID_CONDITIONS = {
    CONDITION_CONTROL_NO_SMELL,
    CONDITION_CLEAN_ODOUR,
    CONDITION_ISOVALERIC_ACID,
}

SMELL_ORDER_CLEAN_THEN_ISO = "control_clean_then_isovaleric"
SMELL_ORDER_ISO_THEN_CLEAN = "control_isovaleric_then_clean"
VALID_SMELL_ORDER_GROUPS = {
    SMELL_ORDER_CLEAN_THEN_ISO,
    SMELL_ORDER_ISO_THEN_CLEAN,
}

TASK_ORDER_IAT_BLOCK_FIRST = "IAT_block_first"
TASK_ORDER_AAT_BLOCK_FIRST = "AAT_block_first"
VALID_TASK_ORDER_GROUPS = {
    TASK_ORDER_IAT_BLOCK_FIRST,
    TASK_ORDER_AAT_BLOCK_FIRST,
}

AAT_COUNTERBALANCE_A = "A"
AAT_COUNTERBALANCE_B = "B"

LOGBOOK_RELATIVE_PATH = Path("logbook") / "MRP_Logbook.xlsx"


@dataclass(frozen=True)
class ParticipantIdentity:
    raw_last4: str
    numeric_id: int


@dataclass(frozen=True)
class RunIdentity:
    participant: ParticipantIdentity
    task: str
    script_type: str
    session_number: int
    condition: str
    task_order_group: str
    smell_order_group: str


def validate_task(task: str) -> str:
    if task not in VALID_TASKS:
        raise ValueError(f"Unsupported task: {task!r}. Expected one of {sorted(VALID_TASKS)}.")
    return task


def validate_script_type(script_type: str) -> str:
    if script_type not in VALID_SCRIPT_TYPES:
        raise ValueError(
            f"Unsupported script type: {script_type!r}. Expected one of {sorted(VALID_SCRIPT_TYPES)}."
        )
    return script_type


def validate_condition(condition: str) -> str:
    if condition not in VALID_CONDITIONS:
        raise ValueError(
            f"Unsupported condition: {condition!r}. Expected one of {sorted(VALID_CONDITIONS)}."
        )
    return condition


def validate_task_order_group(task_order_group: str) -> str:
    if task_order_group not in VALID_TASK_ORDER_GROUPS:
        raise ValueError(
            "Unsupported task order group: "
            f"{task_order_group!r}. Expected one of {sorted(VALID_TASK_ORDER_GROUPS)}."
        )
    return task_order_group


def validate_smell_order_group(smell_order_group: str) -> str:
    if smell_order_group not in VALID_SMELL_ORDER_GROUPS:
        raise ValueError(
            "Unsupported smell order group: "
            f"{smell_order_group!r}. Expected one of {sorted(VALID_SMELL_ORDER_GROUPS)}."
        )
    return smell_order_group


def parse_participant_last4(raw_value: str) -> ParticipantIdentity:
    raw_last4 = str(raw_value).strip()
    if len(raw_last4) != 4 or not raw_last4.isdigit():
        raise ValueError(
            "Participant ID must be exactly the last 4 digits of the participant's phone number."
        )
    return ParticipantIdentity(raw_last4=raw_last4, numeric_id=int(raw_last4))


def format_participant_code(participant_last4: str) -> str:
    participant = parse_participant_last4(participant_last4)
    return f"pid{participant.raw_last4}"


def assign_iat_version(participant_numeric_id: int) -> int:
    if participant_numeric_id < 1:
        raise ValueError("participant_numeric_id must be >= 1.")
    return ((participant_numeric_id - 1) % 4) + 1


def assign_aat_counterbalance(participant_numeric_id: int) -> str:
    if participant_numeric_id < 1:
        raise ValueError("participant_numeric_id must be >= 1.")
    return AAT_COUNTERBALANCE_A if participant_numeric_id % 2 == 0 else AAT_COUNTERBALANCE_B


def smell_condition_order(smell_order_group: str) -> tuple[str, str, str]:
    validate_smell_order_group(smell_order_group)
    if smell_order_group == SMELL_ORDER_CLEAN_THEN_ISO:
        return (
            CONDITION_CONTROL_NO_SMELL,
            CONDITION_CLEAN_ODOUR,
            CONDITION_ISOVALERIC_ACID,
        )
    return (
        CONDITION_CONTROL_NO_SMELL,
        CONDITION_ISOVALERIC_ACID,
        CONDITION_CLEAN_ODOUR,
    )


SMELL_ORDER_CONTROL_THEN_CLEAN_THEN_ISO = smell_condition_order(SMELL_ORDER_CLEAN_THEN_ISO)
SMELL_ORDER_CONTROL_THEN_ISO_THEN_CLEAN = smell_condition_order(SMELL_ORDER_ISO_THEN_CLEAN)


def build_output_filename(
    run: RunIdentity,
    *,
    timestamp: datetime | None = None,
    iat_version: int | None = None,
    suffix: str = ".csv",
) -> str:
    validate_task(run.task)
    validate_script_type(run.script_type)
    validate_condition(run.condition)
    validate_task_order_group(run.task_order_group)
    validate_smell_order_group(run.smell_order_group)

    ts = (timestamp or datetime.now()).strftime("%Y%m%d_%H%M%S")
    base = (
        f"{run.task.lower()}_{run.script_type}_{format_participant_code(run.participant.raw_last4)}"
        f"_s{run.session_number}_{run.condition}_{ts}"
    )
    if run.task == TASK_IAT:
        if iat_version is None:
            raise ValueError("iat_version is required when building an IAT output filename.")
        base = f"{base}_v{iat_version}"
    return f"{base}{suffix}"


def get_project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def get_logbook_override_path() -> Path | None:
    raw_path = os.environ.get("MRP_LOGBOOK_PATH", "").strip()
    if not raw_path:
        return None
    return Path(raw_path).expanduser()


def get_logbook_path(project_root: Path | None = None) -> Path:
    override_path = get_logbook_override_path()
    if override_path is not None:
        return override_path
    root = project_root or get_project_root()
    return root / LOGBOOK_RELATIVE_PATH
