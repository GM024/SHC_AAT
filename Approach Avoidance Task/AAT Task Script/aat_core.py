from __future__ import annotations

import csv
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


SCRIPT_DIR = Path(__file__).resolve().parent
TASK_DIR = SCRIPT_DIR if (SCRIPT_DIR / "data").exists() else SCRIPT_DIR.parent
PROJECT_ROOT = TASK_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.experiment_meta import (
    CONDITION_CONTROL_NO_SMELL,
    RunIdentity,
    SCRIPT_TYPE_MAIN,
    SCRIPT_TYPE_PRACTICE,
    TASK_AAT,
    assign_aat_counterbalance,
    build_output_filename,
    format_participant_code,
    parse_participant_last4,
    smell_condition_order,
)
from shared.logbook import (
    ParticipantLogData,
    RunLogData,
    record_run,
    resolve_participant_assignment,
)


PROJECT_DIR = TASK_DIR
DATA_DIR = PROJECT_DIR / "data"
INTERNAL_DATA_DIR = DATA_DIR / "psychopy_internal"


def resolve_image_root_dir() -> Path:
    candidates = [
        PROJECT_DIR / "material" / "shc_aat_material",
        PROJECT_DIR.parent / "material" / "shc_aat_material",
        PROJECT_DIR / "vaast images and script" / "shc_aat_material",
        Path.cwd() / "material" / "shc_aat_material",
        Path.cwd() / "vaast images and script" / "shc_aat_material",
    ]
    for candidate in candidates:
        if (candidate / "background_shc").exists() and (candidate / "background_fhc").exists():
            return candidate
    return candidates[0]


IMAGE_ROOT_DIR = resolve_image_root_dir()
SHC_IMAGE_DIR = IMAGE_ROOT_DIR / "background_shc"
FHC_IMAGE_DIR = IMAGE_ROOT_DIR / "background_fhc"

FIXATION_DURATION = 0.5
ANIM_DURATION = 0.20
ANIM_FRAMES = 12
PRACTICE_TRIALS_PER_CATEGORY = 4
IMAGE_BASE_MAX_DIM = 0.6
IMAGE_APPROACH_MAX_DIM = 1.0
IMAGE_AVOID_MAX_DIM = 0.3
INSTRUCTION_TEXT_HEIGHT = 0.035
INSTRUCTION_WRAP_WIDTH = 1.4
FORMATTED_LINE_SPACING = 0.047

CLEAN_DATA_COLUMNS = [
    "participant",
    "participant_code",
    "session",
    "task",
    "script_type",
    "condition",
    "smell_order_group",
    "task_order_group",
    "counterbalance",
    "task_start_time_iso",
    "trial_end_time_iso",
    "time_elapsed_ms",
    "block_number",
    "block_name",
    "trial_in_block",
    "trial_global",
    "category",
    "stimulus_number",
    "clothing_type",
    "required_action",
    "correct",
    "rt_ms",
    "incorrect_attempts",
    "correction_required",
    "task_duration_ms",
    "task_duration_s",
]

TRIAL_REPS_PER_BLOCK = 1
WINDOW_SIZE = (1280, 800)
FULLSCREEN = True
BG_COLOR = "black"
EXPECTED_STIMULI_PER_CATEGORY = 25
PRACTICE_SESSION_NUMBER = 0

BUTTON_TO_ACTION = {
    "q": "approach",
    "m": "avoid",
}
QUIT_KEYS = ["escape"]
JOYSTICK_AXIS_THRESHOLD = 0.6
JOYSTICK_AXIS_NEUTRAL = 0.2


@dataclass(frozen=True)
class AATRunSetup:
    run: RunIdentity
    participant_alias: str
    researcher: str
    counterbalance_condition: str


class TaskInterrupted(Exception):
    pass


def require_psychopy():
    from psychopy import core, data, event, gui, visual
    from psychopy.hardware import joystick

    return core, data, event, gui, visual, joystick


def default_participant_alias(participant_id: str) -> str:
    return format_participant_code(participant_id)


def milliseconds_from_seconds(value_sec: float | None) -> int | str:
    if value_sec is None:
        return ""
    return int(round(value_sec * 1000))


def quit_if_requested() -> None:
    _, _, event, _, _, _ = require_psychopy()
    if event.getKeys(keyList=QUIT_KEYS):
        raise TaskInterrupted


def setup_joystick() -> Optional[joystick.Joystick]:
    _, _, _, _, _, joystick = require_psychopy()
    joystick.backend = "pyglet"
    if joystick.getNumJoysticks() < 1:
        return None
    joy = joystick.Joystick(0)
    joy.open()
    return joy


def _poll_joystick_action(
    joy: Optional[joystick.Joystick],
    axis_armed: bool,
) -> Tuple[Optional[str], Optional[str], bool]:
    if joy is None:
        return None, None, axis_armed

    y = joy.getY()
    if abs(y) < JOYSTICK_AXIS_NEUTRAL:
        axis_armed = True
    if axis_armed and y <= -JOYSTICK_AXIS_THRESHOLD:
        return "joy_axis_down", "approach", False
    if axis_armed and y >= JOYSTICK_AXIS_THRESHOLD:
        return "joy_axis_up", "avoid", False

    return None, None, axis_armed


def clothing_type_from_index(idx: int) -> str:
    if 1 <= idx <= 5:
        return "shirt"
    if 6 <= idx <= 10:
        return "pants"
    if 11 <= idx <= 15:
        return "jacket"
    if 16 <= idx <= 20:
        return "hoodie"
    if 21 <= idx <= 25:
        return "beanie"
    return "unknown"


def discover_stimuli(shc_dir: Path, fhc_dir: Path) -> List[Dict[str, str]]:
    if not shc_dir.exists():
        raise FileNotFoundError(f"SHC image folder not found: {shc_dir.resolve()}")
    if not fhc_dir.exists():
        raise FileNotFoundError(f"FHC image folder not found: {fhc_dir.resolve()}")

    trials: List[Dict[str, str]] = []
    valid_ext = {".png", ".jpg", ".jpeg", ".bmp"}

    for category, folder, pattern in (
        ("SHC", shc_dir, r"^shc\d+$"),
        ("FHC", fhc_dir, r"^fhc\d+$"),
    ):
        for path in sorted(folder.glob("*")):
            if not path.is_file() or path.suffix.lower() not in valid_ext:
                continue
            name = path.stem.lower()
            if not re.match(pattern, name):
                continue
            number = int(re.sub(r"^\D+", "", name))
            trials.append(
                {
                    "image_name": path.name,
                    "category": category,
                    "stimulus_number": number,
                    "clothing_type": clothing_type_from_index(number),
                }
            )

    if not trials:
        raise RuntimeError(
            "No SHC/FHC image files found in background folders under "
            f"{IMAGE_ROOT_DIR.resolve()}."
        )

    shc_numbers = {trial["stimulus_number"] for trial in trials if trial["category"] == "SHC"}
    fhc_numbers = {trial["stimulus_number"] for trial in trials if trial["category"] == "FHC"}
    if shc_numbers != fhc_numbers:
        missing_in_fhc = sorted(shc_numbers - fhc_numbers)
        missing_in_shc = sorted(fhc_numbers - shc_numbers)
        raise RuntimeError(
            "Mismatched SHC/FHC stimulus numbers. "
            f"Missing in FHC: {missing_in_fhc}; missing in SHC: {missing_in_shc}"
        )
    if len(shc_numbers) != EXPECTED_STIMULI_PER_CATEGORY:
        raise RuntimeError(
            f"Expected exactly {EXPECTED_STIMULI_PER_CATEGORY} SHC/FHC pairs "
            f"({2 * EXPECTED_STIMULI_PER_CATEGORY} images total), "
            f"but found {len(shc_numbers)} pairs."
        )

    return trials


def stimulus_file_path(trial: Dict[str, str]) -> str:
    folder = SHC_IMAGE_DIR if trial["category"] == "SHC" else FHC_IMAGE_DIR
    return str(folder / trial["image_name"])


def get_block_mapping(counterbalance_condition: str) -> List[Dict[str, Dict[str, str]]]:
    congruent = {"SHC": "approach", "FHC": "avoid"}
    incongruent = {"SHC": "avoid", "FHC": "approach"}

    if counterbalance_condition == "A":
        return [
            {"name": "Congruent", "mapping": congruent},
            {"name": "Incongruent", "mapping": incongruent},
        ]

    return [
        {"name": "Incongruent", "mapping": incongruent},
        {"name": "Congruent", "mapping": congruent},
    ]


def category_label(code: str) -> str:
    labels = {
        "SHC": "second-hand clothing (SHC)",
        "FHC": "first-hand clothing (FHC)",
    }
    return labels.get(code, code)


def _fit_size_within_square(orig_size: Optional[Tuple[float, float]], max_dim: float) -> Tuple[float, float]:
    if not orig_size or len(orig_size) != 2:
        return (max_dim, max_dim)

    width, height = orig_size
    if width <= 0 or height <= 0:
        return (max_dim, max_dim)

    aspect = width / height
    if aspect >= 1.0:
        return (max_dim, max_dim / aspect)
    return (max_dim * aspect, max_dim)


def set_image_stimulus(
    stim: visual.ImageStim,
    image_path: str,
    max_dim: float = IMAGE_BASE_MAX_DIM,
) -> Tuple[float, float]:
    stim.image = image_path
    fitted_size = _fit_size_within_square(getattr(stim, "_origSize", None), max_dim)
    stim.size = fitted_size
    return fitted_size


def animate_response(
    win: visual.Window,
    stim: visual.ImageStim,
    action: str,
    base_size: Tuple[float, float],
) -> None:
    core, _, _, _, _, _ = require_psychopy()
    end_dim = IMAGE_APPROACH_MAX_DIM if action == "approach" else IMAGE_AVOID_MAX_DIM
    end_scale = end_dim / IMAGE_BASE_MAX_DIM

    for frame in range(ANIM_FRAMES):
        t = frame / max(1, ANIM_FRAMES - 1)
        scale = 1.0 + (end_scale - 1.0) * t
        stim.size = (base_size[0] * scale, base_size[1] * scale)
        stim.draw()
        win.flip()

    core.wait(max(0.0, ANIM_DURATION - ANIM_FRAMES * (1 / 60.0)))


def show_text_and_wait(win: visual.Window, text: str, key_list=None) -> List[str]:
    _, _, event, _, visual, _ = require_psychopy()
    allowed_keys = list(key_list or []) + QUIT_KEYS
    msg = visual.TextStim(
        win,
        text=text,
        color="white",
        wrapWidth=INSTRUCTION_WRAP_WIDTH,
        height=INSTRUCTION_TEXT_HEIGHT,
    )
    msg.draw()
    win.flip()
    keys = event.waitKeys(keyList=allowed_keys) or []
    if keys and keys[0] in QUIT_KEYS:
        raise TaskInterrupted
    return keys


def show_formatted_text_and_wait(
    win: visual.Window,
    lines: List[Tuple[str, bool]],
    key_list=None,
) -> List[str]:
    _, _, event, _, visual, _ = require_psychopy()
    allowed_keys = list(key_list or []) + QUIT_KEYS
    start_y = ((len(lines) - 1) * FORMATTED_LINE_SPACING) / 2.0
    for idx, (line_text, is_bold) in enumerate(lines):
        if not line_text:
            continue
        stim = visual.TextStim(
            win,
            text=line_text,
            color="white",
            wrapWidth=INSTRUCTION_WRAP_WIDTH,
            height=INSTRUCTION_TEXT_HEIGHT,
            bold=is_bold,
            pos=(0.0, start_y - idx * FORMATTED_LINE_SPACING),
        )
        stim.draw()
    win.flip()
    keys = event.waitKeys(keyList=allowed_keys) or []
    if keys and keys[0] in QUIT_KEYS:
        raise TaskInterrupted
    return keys


def save_clean_trial_data(rows: List[Dict[str, object]], output_path: Path) -> None:
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CLEAN_DATA_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in CLEAN_DATA_COLUMNS})


def build_practice_trials(
    stimuli: List[Dict[str, str]],
    trials_per_category: int,
) -> List[Dict[str, str]]:
    shc_trials = sorted(
        [trial for trial in stimuli if trial["category"] == "SHC"],
        key=lambda trial: trial["stimulus_number"],
    )[:trials_per_category]
    fhc_trials = sorted(
        [trial for trial in stimuli if trial["category"] == "FHC"],
        key=lambda trial: trial["stimulus_number"],
    )[:trials_per_category]

    practice_trials: List[Dict[str, str]] = []
    for index in range(max(len(shc_trials), len(fhc_trials))):
        if index < len(shc_trials):
            practice_trials.append(shc_trials[index])
        if index < len(fhc_trials):
            practice_trials.append(fhc_trials[index])
    return practice_trials


def collect_response_until_correct(
    win: visual.Window,
    image_stim: visual.ImageStim,
    error_stim: visual.TextStim,
    joy: Optional[joystick.Joystick],
    required_action: str,
) -> Dict[str, Optional[object]]:
    core, _, event, _, _, _ = require_psychopy()
    event.clearEvents(eventType="keyboard")
    axis_armed = abs(joy.getY()) < JOYSTICK_AXIS_NEUTRAL if joy is not None else True
    show_error = False
    clock = core.Clock()
    base_size = tuple(image_stim.size)

    first_key = None
    first_source = None
    first_action = None
    first_rt = None
    incorrect_attempts = 0

    while True:
        quit_if_requested()
        image_stim.draw()
        if show_error:
            error_stim.draw()
        win.flip()

        responded_key = None
        responded_source = None
        responded_action = None
        responded_rt = None

        keys = event.getKeys(
            keyList=list(BUTTON_TO_ACTION.keys()) + QUIT_KEYS,
            timeStamped=clock,
        )
        if keys:
            key, response_time = keys[0]
            if key in QUIT_KEYS:
                raise TaskInterrupted
            responded_key = key
            responded_source = "keyboard_button"
            responded_action = BUTTON_TO_ACTION.get(key)
            responded_rt = response_time
        else:
            joy_key, joy_action, axis_armed = _poll_joystick_action(joy, axis_armed)
            if joy_key is not None:
                responded_key = joy_key
                responded_source = "joystick"
                responded_action = joy_action
                responded_rt = clock.getTime()

        if responded_key is None:
            continue

        if first_key is None:
            first_key = responded_key
            first_source = responded_source
            first_action = responded_action
            first_rt = responded_rt

        if responded_action == required_action:
            animate_response(win, image_stim, responded_action, base_size)
            return {
                "response_key": first_key,
                "response_source": first_source,
                "response_action": first_action,
                "correct": int(first_action == required_action),
                "first_rt": first_rt,
                "rt": responded_rt,
                "final_response_key": responded_key,
                "final_response_source": responded_source,
                "final_response_action": responded_action,
                "final_rt": responded_rt,
                "incorrect_attempts": incorrect_attempts,
                "correction_required": int(incorrect_attempts > 0),
            }

        incorrect_attempts += 1
        show_error = True


def build_run_setup(
    *,
    participant_last4: str,
    script_type: str,
    session_number: int | None,
    smell_order_group: str | None = None,
    task_order_group: str | None = None,
    participant_alias: str = "",
    researcher: str = "",
) -> AATRunSetup:
    participant = parse_participant_last4(participant_last4)
    if smell_order_group is None or task_order_group is None:
        assignment = resolve_participant_assignment(participant.raw_last4)
        smell_order_group = smell_order_group or assignment.smell_order_group
        task_order_group = task_order_group or assignment.task_order_group
    counterbalance_condition = assign_aat_counterbalance(participant.numeric_id)

    if script_type == SCRIPT_TYPE_MAIN:
        if session_number not in (1, 2, 3):
            raise ValueError("Main AAT session_number must be 1, 2, or 3.")
        condition = smell_condition_order(smell_order_group)[session_number - 1]
        resolved_session_number = session_number
    elif script_type == SCRIPT_TYPE_PRACTICE:
        condition = CONDITION_CONTROL_NO_SMELL
        resolved_session_number = PRACTICE_SESSION_NUMBER
    else:
        raise ValueError(f"Unsupported script_type: {script_type}")

    run = RunIdentity(
        participant=participant,
        task=TASK_AAT,
        script_type=script_type,
        session_number=resolved_session_number,
        condition=condition,
        task_order_group=task_order_group,
        smell_order_group=smell_order_group,
    )
    return AATRunSetup(
        run=run,
        participant_alias=participant_alias or default_participant_alias(participant.raw_last4),
        researcher=researcher,
        counterbalance_condition=counterbalance_condition,
    )


def collect_run_setup(script_type: str) -> AATRunSetup:
    _, _, _, gui, _, _ = require_psychopy()
    if script_type == SCRIPT_TYPE_PRACTICE:
        title = "AAT Practice Setup"
    elif script_type == SCRIPT_TYPE_MAIN:
        title = "AAT Main Setup"
    else:
        raise ValueError(f"Unsupported script_type: {script_type}")

    dlg = gui.Dlg(title=title)
    dlg.addText(
        "AAT counterbalancing, smell order, and task order are assigned automatically from the participant ID and logbook."
    )
    dlg.addField("Participant ID (last 4 digits):")
    dlg.addField("Participant alias (optional):")
    dlg.addField("Researcher:")
    if script_type == SCRIPT_TYPE_MAIN:
        dlg.addField("Session number:", choices=["1", "2", "3"])
    if hasattr(dlg, "requiredMsg"):
        dlg.requiredMsg.hide()
    dlg_data = dlg.show()
    if not dlg.OK:
        raise SystemExit

    participant_last4 = str(dlg_data[0]).strip()
    participant_alias = str(dlg_data[1]).strip()
    researcher = str(dlg_data[2]).strip()
    if not researcher:
        raise RuntimeError("Researcher is required.")

    if script_type == SCRIPT_TYPE_MAIN:
        return build_run_setup(
            participant_last4=participant_last4,
            script_type=script_type,
            session_number=int(dlg_data[3]),
            participant_alias=participant_alias,
            researcher=researcher,
        )

    return build_run_setup(
        participant_last4=participant_last4,
        script_type=script_type,
        session_number=None,
        participant_alias=participant_alias,
        researcher=researcher,
    )


def build_output_paths(setup: AATRunSetup) -> dict[str, Path]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    INTERNAL_DATA_DIR.mkdir(parents=True, exist_ok=True)

    raw_csv = DATA_DIR / build_output_filename(setup.run)
    cleaned_csv = raw_csv.with_name(f"{raw_csv.stem}_cleaned.csv")
    internal_base = INTERNAL_DATA_DIR / raw_csv.stem
    return {
        "raw_csv": raw_csv,
        "cleaned_csv": cleaned_csv,
        "internal_base": internal_base,
    }


def create_experiment_handler(setup: AATRunSetup, *, internal_base: Path):
    _, data, _, _, _, _ = require_psychopy()
    exp_name = "AAT_PsychoPy_Practice" if setup.run.script_type == SCRIPT_TYPE_PRACTICE else "AAT_PsychoPy_Main"
    extra_info = {
        "participant": setup.run.participant.raw_last4,
        "participant_code": format_participant_code(setup.run.participant.raw_last4),
        "participant_alias": setup.participant_alias,
        "researcher": setup.researcher,
        "session": setup.run.session_number,
        "script_type": setup.run.script_type,
        "condition": setup.run.condition,
        "smell_order_group": setup.run.smell_order_group,
        "task_order_group": setup.run.task_order_group,
        "counterbalance": setup.counterbalance_condition,
    }
    return data.ExperimentHandler(
        name=exp_name,
        version="1.0",
        extraInfo=extra_info,
        runtimeInfo=None,
        savePickle=False,
        saveWideText=False,
        dataFileName=str(internal_base),
    )


def build_logbook_entries(
    setup: AATRunSetup,
    *,
    output_path: Path,
    status: str,
    notes: str = "",
    run_timestamp: datetime | None = None,
) -> tuple[ParticipantLogData, RunLogData]:
    timestamp = run_timestamp or datetime.now()
    participant_entry = ParticipantLogData(
        participant_id=setup.run.participant.raw_last4,
        participant_display_id=setup.run.participant.raw_last4,
        participant_name_or_alias=setup.participant_alias,
        phone_last4=setup.run.participant.raw_last4,
        session_number=setup.run.session_number if setup.run.session_number in (1, 2, 3) else None,
        session_date=timestamp.date() if setup.run.session_number in (1, 2, 3) else None,
        session_condition=setup.run.condition if setup.run.session_number in (1, 2, 3) else "",
        session_researcher=setup.researcher if setup.run.session_number in (1, 2, 3) else "",
        smell_order_group=setup.run.smell_order_group,
        task_order_group=setup.run.task_order_group,
    )
    run_entry = RunLogData(
        participant_id=setup.run.participant.raw_last4,
        participant_alias=setup.participant_alias,
        task=setup.run.task,
        script_type=setup.run.script_type,
        task_order_group=setup.run.task_order_group,
        smell_order_group=setup.run.smell_order_group,
        run_timestamp=timestamp,
        session_number=setup.run.session_number,
        researcher=setup.researcher,
        condition=setup.run.condition,
        aat_counterbalance=setup.counterbalance_condition,
        output_filename=output_path.name,
        output_path=str(output_path),
        status=status,
        notes=notes,
    )
    return participant_entry, run_entry


def write_aat_logbook_entry(
    setup: AATRunSetup,
    *,
    output_path: Path,
    status: str,
    notes: str = "",
    run_timestamp: datetime | None = None,
    logbook_path: Path | None = None,
):
    participant_entry, run_entry = build_logbook_entries(
        setup,
        output_path=output_path,
        status=status,
        notes=notes,
        run_timestamp=run_timestamp,
    )
    return record_run(participant_entry, run_entry, logbook_path=logbook_path)


def build_cleaned_row(
    setup: AATRunSetup,
    *,
    task_start_time_iso: str,
    trial_end_time_iso: str,
    time_elapsed_ms: int,
    block_number: int,
    block_name: str,
    trial_in_block: int,
    trial_global: int,
    trial: Dict[str, str],
    required_action: str,
    response_data: Dict[str, object],
) -> Dict[str, object]:
    return {
        "participant": setup.run.participant.raw_last4,
        "participant_code": format_participant_code(setup.run.participant.raw_last4),
        "session": setup.run.session_number,
        "task": setup.run.task,
        "script_type": setup.run.script_type,
        "condition": setup.run.condition,
        "smell_order_group": setup.run.smell_order_group,
        "task_order_group": setup.run.task_order_group,
        "counterbalance": setup.counterbalance_condition,
        "task_start_time_iso": task_start_time_iso,
        "trial_end_time_iso": trial_end_time_iso,
        "time_elapsed_ms": time_elapsed_ms,
        "block_number": block_number,
        "block_name": block_name,
        "trial_in_block": trial_in_block,
        "trial_global": trial_global,
        "category": trial["category"],
        "stimulus_number": trial["stimulus_number"],
        "clothing_type": trial["clothing_type"],
        "required_action": required_action,
        "correct": response_data["correct"],
        "rt_ms": milliseconds_from_seconds(response_data["rt"]),
        "incorrect_attempts": response_data["incorrect_attempts"],
        "correction_required": response_data["correction_required"],
    }


def add_trial_handler_data(
    trial_handler,
    setup: AATRunSetup,
    *,
    task_start_time_iso: str,
    trial_end_time_iso: str,
    time_elapsed_ms: int,
    block_number: int,
    block_name: str,
    trial_in_block: int,
    trial_global: int,
    trial: Dict[str, str],
    required_action: str,
    response_data: Dict[str, object],
) -> None:
    trial_handler.addData("participant", setup.run.participant.raw_last4)
    trial_handler.addData("participant_code", format_participant_code(setup.run.participant.raw_last4))
    trial_handler.addData("session", setup.run.session_number)
    trial_handler.addData("task", setup.run.task)
    trial_handler.addData("script_type", setup.run.script_type)
    trial_handler.addData("condition", setup.run.condition)
    trial_handler.addData("smell_order_group", setup.run.smell_order_group)
    trial_handler.addData("task_order_group", setup.run.task_order_group)
    trial_handler.addData("counterbalance", setup.counterbalance_condition)
    trial_handler.addData("task_start_time_iso", task_start_time_iso)
    trial_handler.addData("trial_end_time_iso", trial_end_time_iso)
    trial_handler.addData("time_elapsed_ms", time_elapsed_ms)
    trial_handler.addData("block_number", block_number)
    trial_handler.addData("block_name", block_name)
    trial_handler.addData("trial_in_block", trial_in_block)
    trial_handler.addData("trial_global", trial_global)
    trial_handler.addData("image_name", trial["image_name"])
    trial_handler.addData("category", trial["category"])
    trial_handler.addData("stimulus_number", trial["stimulus_number"])
    trial_handler.addData("clothing_type", trial["clothing_type"])
    trial_handler.addData("required_action", required_action)
    trial_handler.addData("response_key", response_data["response_key"])
    trial_handler.addData("response_source", response_data["response_source"])
    trial_handler.addData("response_action", response_data["response_action"])
    trial_handler.addData("correct", response_data["correct"])
    trial_handler.addData("rt", response_data["rt"])
    trial_handler.addData("rt_ms", milliseconds_from_seconds(response_data["rt"]))
    trial_handler.addData("final_response_key", response_data["final_response_key"])
    trial_handler.addData("final_response_source", response_data["final_response_source"])
    trial_handler.addData("final_response_action", response_data["final_response_action"])
    trial_handler.addData("incorrect_attempts", response_data["incorrect_attempts"])
    trial_handler.addData("correction_required", response_data["correction_required"])


def practice_instruction_lines(block: Dict[str, Dict[str, str]]) -> List[Tuple[str, bool]]:
    mapping = block["mapping"]
    approach_cats = [category_label(code) for code, action in mapping.items() if action == "approach"]
    avoid_cats = [category_label(code) for code, action in mapping.items() if action == "avoid"]
    return [
        (f"Practice: {block['name']}", True),
        ("", False),
        ("You'll see two different types of clothing.", False),
        ("SHC means second-hand clothing, and FHC means first-hand clothing.", False),
        ("", False),
        ("In this block:", False),
        (f"Approach {', '.join(approach_cats)}.", False),
        (f"Avoid {', '.join(avoid_cats)}.", False),
        ("", False),
        ("Move the joystick backward (pull the joystick) to approach the picture,", False),
        ("and move the joystick forward (push the joystick) to avoid the picture.", False),
        ("If a joystick is not available, use the equivalent response keys:", False),
        ("Q = approach, M = avoid.", False),
        ("", False),
        ("If you respond incorrectly, an X will appear while the picture remains", False),
        ("visible on the screen.", False),
        ("You cannot continue to the next trial until you make the correct", False),
        ("response. The trial will continue as soon as you respond correctly.", False),
        ("", False),
        ("Press SPACE to begin the practice block.", False),
    ]


def main_instruction_lines(block: Dict[str, Dict[str, str]]) -> List[Tuple[str, bool]]:
    mapping = block["mapping"]
    approach_cats = [category_label(code) for code, action in mapping.items() if action == "approach"]
    avoid_cats = [category_label(code) for code, action in mapping.items() if action == "avoid"]
    return [
        ((f"Block: {block['name']}"), True),
        ("", False),
        ("In this block:", False),
        (f"Approach {', '.join(approach_cats)} by pulling the joystick", False),
        ("backward (or pressing Q if no joystick is available).", False),
        (f"Avoid {', '.join(avoid_cats)} by pushing the joystick forward", False),
        ("(or pressing M if no joystick is available).", False),
        ("", False),
        ("If you respond incorrectly, an X will appear while the picture remains", False),
        ("visible on the screen.", False),
        ("You cannot continue to the next trial until you make the correct", False),
        ("response. The trial will continue as soon as you respond correctly.", False),
        ("", False),
        ("Press SPACE to begin the block.", False),
    ]


def run_practice_blocks(
    setup: AATRunSetup,
    *,
    win: visual.Window,
    fixation: visual.TextStim,
    image_stim: visual.ImageStim,
    error_stim: visual.TextStim,
    joy: Optional[joystick.Joystick],
    stimuli: List[Dict[str, str]],
    task_start_time_iso: str,
    task_clock,
    this_exp,
) -> List[Dict[str, object]]:
    core, data, _, _, _, _ = require_psychopy()
    cleaned_rows: List[Dict[str, object]] = []
    practice_trials = build_practice_trials(stimuli, PRACTICE_TRIALS_PER_CATEGORY)
    blocks = get_block_mapping(setup.counterbalance_condition)
    global_trial_index = 0

    show_text_and_wait(
        win,
        "You'll see two different types of clothing.\n"
        "SHC means second-hand clothing, and FHC means first-hand clothing.\n\n"
        "Move the joystick backward (pull the joystick) to approach the\n"
        "picture, and move the joystick forward (push the joystick) to avoid\n"
        "the picture.\n"
        "If a joystick is not available, use the equivalent response keys:\n"
        "Q = approach, M = avoid.\n\n"
        "You will complete short practice blocks only.\n"
        "If you respond incorrectly, an X will appear while the picture remains\n"
        "visible on the screen.\n"
        "You cannot continue to the next trial until you make the correct\n"
        "response. The trial will continue as soon as you respond correctly.\n"
        "This rule applies to all practice trials.\n\n"
        "Please respond as quickly and accurately as possible.\n"
        "Press SPACE to start.",
        key_list=["space"],
    )

    for block_idx, block in enumerate(blocks, start=1):
        show_formatted_text_and_wait(
            win,
            practice_instruction_lines(block),
            key_list=["space"],
        )

        trial_handler = data.TrialHandler(practice_trials, nReps=1, method="random")
        this_exp.addLoop(trial_handler)

        for trial_idx, trial in enumerate(trial_handler, start=1):
            quit_if_requested()
            global_trial_index += 1

            fixation.draw()
            win.flip()
            core.wait(FIXATION_DURATION)

            set_image_stimulus(image_stim, stimulus_file_path(trial))
            required_action = block["mapping"][trial["category"]]
            response_data = collect_response_until_correct(
                win=win,
                image_stim=image_stim,
                error_stim=error_stim,
                joy=joy,
                required_action=required_action,
            )
            trial_end_timestamp = datetime.now()
            time_elapsed_ms = int(round(task_clock.getTime() * 1000))

            add_trial_handler_data(
                trial_handler,
                setup,
                task_start_time_iso=task_start_time_iso,
                trial_end_time_iso=trial_end_timestamp.isoformat(timespec="milliseconds"),
                time_elapsed_ms=time_elapsed_ms,
                block_number=block_idx,
                block_name=block["name"],
                trial_in_block=trial_idx,
                trial_global=global_trial_index,
                trial=trial,
                required_action=required_action,
                response_data=response_data,
            )
            cleaned_rows.append(
                build_cleaned_row(
                    setup,
                    task_start_time_iso=task_start_time_iso,
                    trial_end_time_iso=trial_end_timestamp.isoformat(timespec="milliseconds"),
                    time_elapsed_ms=time_elapsed_ms,
                    block_number=block_idx,
                    block_name=block["name"],
                    trial_in_block=trial_idx,
                    trial_global=global_trial_index,
                    trial=trial,
                    required_action=required_action,
                    response_data=response_data,
                )
            )
            this_exp.nextEntry()

        if block_idx < len(blocks):
            show_text_and_wait(
                win,
                f"End of practice block {block_idx}.\n\nPress SPACE to continue.",
                key_list=["space"],
            )

    show_text_and_wait(
        win,
        "Practice complete.\n\nThank you.\nPress SPACE to exit.",
        key_list=["space"],
    )
    return cleaned_rows


def run_main_blocks(
    setup: AATRunSetup,
    *,
    win: visual.Window,
    fixation: visual.TextStim,
    image_stim: visual.ImageStim,
    error_stim: visual.TextStim,
    joy: Optional[joystick.Joystick],
    stimuli: List[Dict[str, str]],
    task_start_time_iso: str,
    task_clock,
    this_exp,
) -> List[Dict[str, object]]:
    core, data, _, _, _, _ = require_psychopy()
    cleaned_rows: List[Dict[str, object]] = []
    blocks = get_block_mapping(setup.counterbalance_condition)
    total_trials = len(stimuli) * TRIAL_REPS_PER_BLOCK * len(blocks)
    if total_trials != 100:
        raise RuntimeError(f"Task misconfigured: expected 100 total trials, got {total_trials}.")

    show_text_and_wait(
        win,
        "You'll see two different types of clothing.\n"
        "SHC means second-hand clothing, and FHC means first-hand clothing.\n\n"
        "Move the joystick backward (pull the joystick) to approach the\n"
        "picture, and move the joystick forward (push the joystick) to avoid\n"
        "the picture.\n"
        "If a joystick is not available, use the equivalent response keys:\n"
        "Q = approach, M = avoid.\n\n"
        "If you respond incorrectly, an X will appear while the picture remains\n"
        "visible on the screen.\n"
        "You cannot continue to the next trial until you make the correct\n"
        "response. The trial will continue as soon as you respond correctly.\n"
        "This rule applies to all test trials.\n\n"
        "Please respond as quickly and accurately as possible.\n"
        "Press SPACE to start.",
        key_list=["space"],
    )

    global_trial_index = 0

    for block_idx, block in enumerate(blocks, start=1):
        show_formatted_text_and_wait(
            win,
            main_instruction_lines(block),
            key_list=["space"],
        )

        block_trials = stimuli * TRIAL_REPS_PER_BLOCK
        trial_handler = data.TrialHandler(block_trials, nReps=1, method="random")
        this_exp.addLoop(trial_handler)

        for trial_idx, trial in enumerate(trial_handler, start=1):
            quit_if_requested()
            global_trial_index += 1

            fixation.draw()
            win.flip()
            core.wait(FIXATION_DURATION)

            set_image_stimulus(image_stim, stimulus_file_path(trial))
            required_action = block["mapping"][trial["category"]]
            response_data = collect_response_until_correct(
                win=win,
                image_stim=image_stim,
                error_stim=error_stim,
                joy=joy,
                required_action=required_action,
            )
            trial_end_timestamp = datetime.now()
            time_elapsed_ms = int(round(task_clock.getTime() * 1000))

            add_trial_handler_data(
                trial_handler,
                setup,
                task_start_time_iso=task_start_time_iso,
                trial_end_time_iso=trial_end_timestamp.isoformat(timespec="milliseconds"),
                time_elapsed_ms=time_elapsed_ms,
                block_number=block_idx,
                block_name=block["name"],
                trial_in_block=trial_idx,
                trial_global=global_trial_index,
                trial=trial,
                required_action=required_action,
                response_data=response_data,
            )
            cleaned_rows.append(
                build_cleaned_row(
                    setup,
                    task_start_time_iso=task_start_time_iso,
                    trial_end_time_iso=trial_end_timestamp.isoformat(timespec="milliseconds"),
                    time_elapsed_ms=time_elapsed_ms,
                    block_number=block_idx,
                    block_name=block["name"],
                    trial_in_block=trial_idx,
                    trial_global=global_trial_index,
                    trial=trial,
                    required_action=required_action,
                    response_data=response_data,
                )
            )
            this_exp.nextEntry()

        show_text_and_wait(
            win,
            f"End of Block {block_idx}.\n\nPress SPACE to continue.",
            key_list=["space"],
        )

    show_text_and_wait(
        win,
        "Task complete.\n\nThank you for your participation.\nPress SPACE to exit.",
        key_list=["space"],
    )
    return cleaned_rows


def run_aat(script_type: str) -> None:
    core, _, _, _, visual, _ = require_psychopy()
    setup = collect_run_setup(script_type)
    output_paths = build_output_paths(setup)
    this_exp = create_experiment_handler(setup, internal_base=output_paths["internal_base"])
    win = None
    task_clock = None
    cleaned_rows: List[Dict[str, object]] = []
    status = "completed"
    notes = ""
    pending_error: Exception | None = None

    try:
        win = visual.Window(
            size=WINDOW_SIZE,
            fullscr=FULLSCREEN,
            color=BG_COLOR,
            units="height",
        )
        task_clock = core.Clock()
        task_start_timestamp = datetime.now()
        task_start_time_iso = task_start_timestamp.isoformat(timespec="milliseconds")
        this_exp.extraInfo["task_start_time_iso"] = task_start_time_iso

        fixation = visual.TextStim(win, text="+", color="white", height=0.08)
        error_stim = visual.TextStim(win, text="X", color="red", height=0.16, bold=True)
        image_stim = visual.ImageStim(win, image=None, size=(IMAGE_BASE_MAX_DIM, IMAGE_BASE_MAX_DIM))
        joy = setup_joystick()
        stimuli = discover_stimuli(SHC_IMAGE_DIR, FHC_IMAGE_DIR)

        if script_type == SCRIPT_TYPE_PRACTICE:
            cleaned_rows = run_practice_blocks(
                setup,
                win=win,
                fixation=fixation,
                image_stim=image_stim,
                error_stim=error_stim,
                joy=joy,
                stimuli=stimuli,
                task_start_time_iso=task_start_time_iso,
                task_clock=task_clock,
                this_exp=this_exp,
            )
        elif script_type == SCRIPT_TYPE_MAIN:
            cleaned_rows = run_main_blocks(
                setup,
                win=win,
                fixation=fixation,
                image_stim=image_stim,
                error_stim=error_stim,
                joy=joy,
                stimuli=stimuli,
                task_start_time_iso=task_start_time_iso,
                task_clock=task_clock,
                this_exp=this_exp,
            )
        else:
            raise ValueError(f"Unsupported script_type: {script_type}")
    except TaskInterrupted:
        status = "interrupted"
    except Exception as exc:
        status = "invalid"
        notes = f"{type(exc).__name__}: {exc}"
        pending_error = exc
    finally:
        if win is not None:
            win.close()

    if task_clock is not None:
        task_duration_s = task_clock.getTime()
        task_duration_ms = int(round(task_duration_s * 1000))
        this_exp.extraInfo["task_duration_s"] = task_duration_s
        this_exp.extraInfo["task_duration_ms"] = task_duration_ms
        for row in cleaned_rows:
            row["task_duration_ms"] = task_duration_ms
            row["task_duration_s"] = task_duration_s

    save_exception: Exception | None = None
    try:
        this_exp.saveAsWideText(str(output_paths["raw_csv"]))
        save_clean_trial_data(cleaned_rows, output_paths["cleaned_csv"])
    except Exception as exc:
        save_exception = exc
        save_note = f"save_failed={type(exc).__name__}: {exc}"
        notes = f"{notes} | {save_note}".strip(" |")
        if pending_error is None and status == "completed":
            status = "invalid"
            pending_error = exc

    try:
        write_aat_logbook_entry(
            setup,
            output_path=output_paths["raw_csv"],
            status=status,
            notes=notes,
        )
    except Exception:
        if pending_error is None:
            raise

    if pending_error is not None:
        raise pending_error
    if save_exception is not None and status == "interrupted":
        return
