from __future__ import annotations

import csv
import random
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


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
    TASK_IAT,
    assign_iat_version,
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


VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff"}

TRIALS_PRACTICE_BLOCK = 10
TRIALS_MAIN_BLOCK = 72
PRACTICE_SESSION_NUMBER = 0
PRACTICE_FIXED_SUBSET_SIZE = 10

FIXATION_SEC = 0.30
ITI_SEC = 0.15
IMAGE_BOUND_SIZE = (0.55, 0.55)

KEY_LEFT = "e"
KEY_RIGHT = "i"
QUIT_KEYS = ["escape"]

CAT_SHC = "SHC"
CAT_DISEASE = "Disease"
CAT_DANGER = "Danger"

DISEASE_PATTERNS = ["*injuries_infections*.jpg", "*hygiene*.jpg", "*body products*.jpg"]

INSTRUCTION_WRAP_RATIO = 0.82
INSTRUCTION_HEIGHT_RATIO = 0.82
INSTRUCTION_TITLE_GAP_PX = 28
INSTRUCTION_TITLE_HEIGHT_PX = 40
INSTRUCTION_BODY_HEIGHT_PX = 28
INSTRUCTION_MIN_TITLE_HEIGHT_PX = 28
INSTRUCTION_MIN_BODY_HEIGHT_PX = 18


@dataclass(frozen=True)
class IATRunSetup:
    run: RunIdentity
    participant_alias: str
    researcher: str
    iat_version: int
    version_source: str
    version_cfg: dict[str, str]


class TaskInterrupted(Exception):
    pass


def require_psychopy():
    from psychopy import core, event, gui, visual

    return core, event, gui, visual


def default_participant_alias(participant_id: str) -> str:
    return format_participant_code(participant_id)


def milliseconds_from_seconds(value_sec: float | None) -> int | str:
    if value_sec is None:
        return ""
    return int(round(value_sec * 1000))


def resolve_stim_root() -> Path:
    candidates = [
        TASK_DIR / "material",
        PROJECT_ROOT / "material",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def resolve_existing_dir(candidates: list[Path], label: str) -> Path:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    candidate_text = "\n".join(str(candidate) for candidate in candidates)
    raise RuntimeError(f"Could not locate {label}. Checked:\n{candidate_text}")


def resolve_shc_dir(stim_root: Path) -> Path:
    candidates = [
        stim_root / "background_shc",
        stim_root / "background_SHC",
        stim_root / "shc_aat_material" / "background_shc",
        stim_root / "shc_aat_material" / "background_SHC",
    ]
    return resolve_existing_dir(candidates, "SHC stimulus folder")


def resolve_disgust_dir(stim_root: Path) -> Path:
    candidates = [
        stim_root / "disgust",
        stim_root / "DIRTI_database" / "DIRTI Database",
        stim_root / "DIRTI Database",
        stim_root / "danger" / "DIRTI_database" / "DIRTI Database",
        stim_root / "danger" / "DIRTI Database",
    ]
    return resolve_existing_dir(candidates, "disease/disgust stimulus folder")


def resolve_danger_dir(stim_root: Path) -> Path:
    candidates = [
        stim_root / "danger" / "accepted",
    ]
    return resolve_existing_dir(candidates, "danger stimulus folder")


def load_stimuli(folder: Path, recursive: bool = False) -> list[Path]:
    if not folder.exists():
        raise RuntimeError(f"Stimulus folder does not exist: {folder}")
    iterator = folder.rglob("*") if recursive else folder.iterdir()
    files = [p for p in iterator if p.is_file() and p.suffix.lower() in VALID_EXTENSIONS]
    if not files:
        raise RuntimeError(f"No valid image files found in: {folder}")
    return sorted(files)


def load_stimuli_from_patterns(folder: Path, patterns: list[str]) -> list[Path]:
    if not folder.exists():
        raise RuntimeError(f"Stimulus folder does not exist: {folder}")
    files: list[Path] = []
    for pattern in patterns:
        files.extend(
            [p for p in folder.glob(pattern) if p.is_file() and p.suffix.lower() in VALID_EXTENSIONS]
        )
    unique_files = sorted(set(files))
    if not unique_files:
        raise RuntimeError(f"No files found for patterns {patterns} in: {folder}")
    return unique_files


def load_stimulus_pools() -> dict[str, list[Path]]:
    stim_root = resolve_stim_root()
    return {
        CAT_SHC: load_stimuli(resolve_shc_dir(stim_root)),
        CAT_DISEASE: load_stimuli_from_patterns(resolve_disgust_dir(stim_root), DISEASE_PATTERNS),
        CAT_DANGER: load_stimuli(resolve_danger_dir(stim_root), recursive=True),
    }


def build_practice_pools(stimulus_pools: dict[str, list[Path]]) -> dict[str, list[Path]]:
    practice_pools: dict[str, list[Path]] = {}
    for category, files in stimulus_pools.items():
        subset = files[:PRACTICE_FIXED_SUBSET_SIZE]
        if not subset:
            raise RuntimeError(f"No practice stimuli available for {category}.")
        practice_pools[category] = subset
    return practice_pools


def get_version_config(iat_version: int) -> dict[str, str]:
    version_map = {
        1: {"order_condition": "disease_first", "side_condition": "combined_left"},
        2: {"order_condition": "disease_first", "side_condition": "combined_right"},
        3: {"order_condition": "danger_first", "side_condition": "combined_left"},
        4: {"order_condition": "danger_first", "side_condition": "combined_right"},
    }
    if iat_version not in version_map:
        raise ValueError("iat_version must be 1, 2, 3, or 4.")
    cfg = dict(version_map[iat_version])
    cfg["iat_version"] = str(iat_version)
    cfg["first_combined_mapping"] = (
        "shc_disease_vs_danger"
        if cfg["order_condition"] == "disease_first"
        else "shc_danger_vs_disease"
    )
    cfg["second_combined_mapping"] = (
        "shc_danger_vs_disease"
        if cfg["first_combined_mapping"] == "shc_disease_vs_danger"
        else "shc_disease_vs_danger"
    )
    return cfg


def mapping_recipe(mapping_name: str, side_condition: str) -> dict[str, str]:
    if mapping_name == "shc_disease_vs_danger":
        if side_condition == "combined_left":
            return {CAT_SHC: KEY_LEFT, CAT_DISEASE: KEY_LEFT, CAT_DANGER: KEY_RIGHT}
        return {CAT_DANGER: KEY_LEFT, CAT_SHC: KEY_RIGHT, CAT_DISEASE: KEY_RIGHT}

    if mapping_name == "shc_danger_vs_disease":
        if side_condition == "combined_left":
            return {CAT_SHC: KEY_LEFT, CAT_DANGER: KEY_LEFT, CAT_DISEASE: KEY_RIGHT}
        return {CAT_DISEASE: KEY_LEFT, CAT_SHC: KEY_RIGHT, CAT_DANGER: KEY_RIGHT}

    raise ValueError(f"Unknown mapping_name: {mapping_name}")


def attribute_practice_recipe(first_combined_mapping: str, side_condition: str) -> dict[str, str]:
    if first_combined_mapping == "shc_disease_vs_danger":
        if side_condition == "combined_left":
            return {CAT_DISEASE: KEY_LEFT, CAT_DANGER: KEY_RIGHT}
        return {CAT_DANGER: KEY_LEFT, CAT_DISEASE: KEY_RIGHT}
    if side_condition == "combined_left":
        return {CAT_DANGER: KEY_LEFT, CAT_DISEASE: KEY_RIGHT}
    return {CAT_DISEASE: KEY_LEFT, CAT_DANGER: KEY_RIGHT}


def balanced_counts_from_recipe(recipe: dict[str, str], n_trials: int) -> dict[str, int]:
    categories = list(recipe.keys())
    base_count = n_trials // len(categories)
    remainder = n_trials % len(categories)
    counts = {category: base_count for category in categories}
    for category in categories[:remainder]:
        counts[category] += 1
    return counts


def main_counts_for_mapping(mapping_name: str) -> dict[str, int]:
    if mapping_name == "shc_disease_vs_danger":
        return {CAT_SHC: 21, CAT_DISEASE: 21, CAT_DANGER: 30}
    if mapping_name == "shc_danger_vs_disease":
        return {CAT_SHC: 21, CAT_DANGER: 21, CAT_DISEASE: 30}
    raise ValueError(f"Unknown main mapping_name: {mapping_name}")


def build_practice_blocks(version_cfg: dict[str, str]) -> list[dict[str, object]]:
    first_map = version_cfg["first_combined_mapping"]
    second_map = version_cfg["second_combined_mapping"]
    side = version_cfg["side_condition"]
    first_practice_recipe = attribute_practice_recipe(first_map, side)
    first_combined_recipe = mapping_recipe(first_map, side)
    second_combined_recipe = mapping_recipe(second_map, side)

    blocks = [
        {
            "block_num": 1,
            "block_name": "Practice 1",
            "block_type": "practice",
            "mapping_name": "Disease vs Danger",
            "n_trials": TRIALS_PRACTICE_BLOCK,
            "trial_recipe": first_practice_recipe,
            "category_counts": balanced_counts_from_recipe(first_practice_recipe, TRIALS_PRACTICE_BLOCK),
            "stimulus_mode": "fixed_subset",
        },
        {
            "block_num": 2,
            "block_name": "Combined practice",
            "block_type": "practice",
            "mapping_name": first_map,
            "n_trials": TRIALS_PRACTICE_BLOCK,
            "trial_recipe": first_combined_recipe,
            "category_counts": balanced_counts_from_recipe(
                first_combined_recipe, TRIALS_PRACTICE_BLOCK
            ),
            "stimulus_mode": "fixed_subset",
        },
        {
            "block_num": 3,
            "block_name": "Reversed combined practice",
            "block_type": "practice",
            "mapping_name": second_map,
            "n_trials": TRIALS_PRACTICE_BLOCK,
            "trial_recipe": second_combined_recipe,
            "category_counts": balanced_counts_from_recipe(
                second_combined_recipe, TRIALS_PRACTICE_BLOCK
            ),
            "stimulus_mode": "fixed_subset",
        },
    ]
    validate_blocks(blocks, script_type=SCRIPT_TYPE_PRACTICE)
    return blocks


def build_main_blocks(version_cfg: dict[str, str]) -> list[dict[str, object]]:
    first_map = version_cfg["first_combined_mapping"]
    second_map = version_cfg["second_combined_mapping"]
    side = version_cfg["side_condition"]

    blocks = [
        {
            "block_num": 1,
            "block_name": "Combined test",
            "block_type": "test",
            "mapping_name": first_map,
            "n_trials": TRIALS_MAIN_BLOCK,
            "trial_recipe": mapping_recipe(first_map, side),
            "category_counts": main_counts_for_mapping(first_map),
            "stimulus_mode": "unique_within_block",
        },
        {
            "block_num": 2,
            "block_name": "Reversed combined test",
            "block_type": "test",
            "mapping_name": second_map,
            "n_trials": TRIALS_MAIN_BLOCK,
            "trial_recipe": mapping_recipe(second_map, side),
            "category_counts": main_counts_for_mapping(second_map),
            "stimulus_mode": "unique_within_block",
        },
    ]
    validate_blocks(blocks, script_type=SCRIPT_TYPE_MAIN)
    return blocks


def validate_blocks(blocks: list[dict[str, object]], *, script_type: str) -> None:
    if script_type == SCRIPT_TYPE_PRACTICE:
        expected_block_count = 3
        expected_trials = TRIALS_PRACTICE_BLOCK
    elif script_type == SCRIPT_TYPE_MAIN:
        expected_block_count = 2
        expected_trials = TRIALS_MAIN_BLOCK
    else:
        raise ValueError(f"Unsupported script_type: {script_type}")

    if len(blocks) != expected_block_count:
        raise RuntimeError(
            f"{script_type} IAT requires {expected_block_count} blocks, found {len(blocks)}."
        )

    for block in blocks:
        block_num = int(block["block_num"])
        n_trials = int(block["n_trials"])
        category_counts = dict(block["category_counts"])
        if n_trials != expected_trials:
            raise RuntimeError(
                f"Block {block_num} has {n_trials} trials, expected {expected_trials}."
            )
        if sum(category_counts.values()) != n_trials:
            raise RuntimeError(
                f"Block {block_num} category counts sum to {sum(category_counts.values())}, "
                f"expected {n_trials}."
            )

    if script_type == SCRIPT_TYPE_MAIN:
        for block in blocks:
            sorted_counts = sorted(dict(block["category_counts"]).values())
            if sorted_counts != [21, 21, 30]:
                raise RuntimeError(
                    f"Main block {block['block_num']} must follow 21/21/30, got {sorted_counts}."
                )


def build_block_trials(
    block: dict[str, object],
    stimulus_pools: dict[str, list[Path]],
    rng: random.Random,
) -> list[dict[str, str]]:
    recipe = dict(block["trial_recipe"])
    counts = dict(block["category_counts"])
    trials: list[dict[str, str]] = []

    for category, count in counts.items():
        pool = stimulus_pools[category]
        if len(pool) < count:
            raise RuntimeError(
                f"Not enough unique stimuli for {category} in block {block['block_name']}: "
                f"need {count}, found {len(pool)}."
            )

        if block["stimulus_mode"] == "fixed_subset":
            selected_files = pool[:count]
        elif block["stimulus_mode"] == "unique_within_block":
            selected_files = rng.sample(pool, count)
        else:
            raise ValueError(f"Unknown stimulus_mode: {block['stimulus_mode']}")

        for stimulus_file in selected_files:
            trials.append(
                {
                    "stimulus_category": category,
                    "stimulus_file": str(stimulus_file),
                    "correct_response": recipe[category],
                }
            )

    rng.shuffle(trials)
    return trials


def display_category_name(category_name: str) -> str:
    if category_name == CAT_DISEASE:
        return "disease/disgust"
    if category_name == CAT_DANGER:
        return "danger/fear"
    return category_name


def labels_for_block(block: dict[str, object]) -> tuple[str, str]:
    recipe = dict(block["trial_recipe"])
    left_cats = [display_category_name(cat) for cat, key in recipe.items() if key == KEY_LEFT]
    right_cats = [display_category_name(cat) for cat, key in recipe.items() if key == KEY_RIGHT]
    left_label = f"LEFT ({KEY_LEFT.upper()}): " + " + ".join(left_cats)
    right_label = f"RIGHT ({KEY_RIGHT.upper()}): " + " + ".join(right_cats)
    return left_label, right_label


def mapping_display_name(mapping_name: str) -> str:
    if mapping_name == "Disease vs Danger":
        return "disease/disgust vs danger/fear"
    if mapping_name == "shc_disease_vs_danger":
        return "SHC + disease/disgust vs danger/fear"
    if mapping_name == "shc_danger_vs_disease":
        return "SHC + danger/fear vs disease/disgust"
    return mapping_name


def instruction_categories(label_text: str) -> str:
    if ":" in label_text:
        return label_text.split(":", 1)[1].strip()
    return label_text.replace(f"({KEY_LEFT.upper()})", "").replace(
        f"({KEY_RIGHT.upper()})", ""
    ).strip()


def build_instruction_stim(win, text: str, height_px: int, wrap_width_px: int, *, bold=False, color="white"):
    _, _, _, visual = require_psychopy()
    return visual.TextStim(
        win,
        text=text,
        color=color,
        units="pix",
        height=height_px,
        wrapWidth=wrap_width_px,
        alignText="center",
        bold=bold,
    )


def fit_instruction_stims(win, title: str | None, text: str, *, title_color: str):
    max_width_px = int(win.size[0] * INSTRUCTION_WRAP_RATIO)
    max_height_px = int(win.size[1] * INSTRUCTION_HEIGHT_RATIO)

    body_start_height_px = INSTRUCTION_BODY_HEIGHT_PX if title else INSTRUCTION_BODY_HEIGHT_PX + 2
    last_title_stim = None
    last_body_stim = None

    for body_height_px in range(body_start_height_px, INSTRUCTION_MIN_BODY_HEIGHT_PX - 1, -1):
        body_stim = build_instruction_stim(win, text, body_height_px, max_width_px)
        last_body_stim = body_stim

        if title is None:
            if body_stim.boundingBox[1] <= max_height_px and body_stim.boundingBox[0] <= max_width_px + 2:
                return None, body_stim
            continue

        for title_height_px in range(INSTRUCTION_TITLE_HEIGHT_PX, INSTRUCTION_MIN_TITLE_HEIGHT_PX - 1, -1):
            title_stim = build_instruction_stim(
                win,
                title,
                title_height_px,
                max_width_px,
                bold=True,
                color=title_color,
            )
            last_title_stim = title_stim
            combined_height_px = (
                title_stim.boundingBox[1] + INSTRUCTION_TITLE_GAP_PX + body_stim.boundingBox[1]
            )
            combined_width_px = max(title_stim.boundingBox[0], body_stim.boundingBox[0])
            if combined_height_px <= max_height_px and combined_width_px <= max_width_px + 2:
                return title_stim, body_stim

    if title is None:
        return None, last_body_stim
    return last_title_stim, last_body_stim


def wait_for_instruction_advance():
    _, event, _, _ = require_psychopy()
    keys = event.waitKeys(keyList=["space"] + QUIT_KEYS)
    if keys and keys[0] in QUIT_KEYS:
        raise TaskInterrupted


def show_instruction_screen(win, text: str, title: str | None = None, *, title_color="white"):
    title_stim, body_stim = fit_instruction_stims(win, title, text, title_color=title_color)

    if title_stim is None:
        body_stim.pos = (0.0, 0.0)
        body_stim.draw()
    else:
        title_height_px = title_stim.boundingBox[1]
        body_height_px = body_stim.boundingBox[1]
        combined_height_px = title_height_px + INSTRUCTION_TITLE_GAP_PX + body_height_px
        top_y = combined_height_px / 2
        title_stim.pos = (0.0, top_y - title_height_px / 2)
        body_stim.pos = (
            0.0,
            top_y - title_height_px - INSTRUCTION_TITLE_GAP_PX - body_height_px / 2,
        )
        title_stim.draw()
        body_stim.draw()

    win.flip()
    wait_for_instruction_advance()


def show_initial_instruction(win, *, script_type: str):
    text = (
        "You will categorize images using two keys.\n"
        "In this task, SHC stands for second-hand clothing.\n"
        f"Press '{KEY_LEFT.upper()}' for the left category and\n"
        f"'{KEY_RIGHT.upper()}' for the right category.\n"
        "Respond as quickly and accurately as possible.\n"
        "If your first response is incorrect, a red X will appear while\n"
        "the picture and labels stay visible on the screen.\n"
        "Press the correct key to continue to the next trial.\n"
        "Press SPACE to start."
    )
    if script_type == SCRIPT_TYPE_PRACTICE:
        show_instruction_screen(win, text, title="PRACTICE", title_color="red")
        return
    show_instruction_screen(win, text, title="Instructions")


def show_block_instruction(win, block: dict[str, object], left_label: str, right_label: str, *, script_type: str):
    title = str(block["block_name"])
    title_color = "white"
    if script_type == SCRIPT_TYPE_PRACTICE:
        title = f"PRACTICE\n{title}"
        title_color = "red"

    text = (
        f"Mapping: {mapping_display_name(str(block['mapping_name']))}\n\n"
        f"Press '{KEY_LEFT.upper()}' for LEFT: {instruction_categories(left_label).replace(chr(10), ' ')}.\n"
        f"Press '{KEY_RIGHT.upper()}' for RIGHT: {instruction_categories(right_label).replace(chr(10), ' ')}.\n\n"
        "If your first response is incorrect, a red X will appear while the picture and labels stay visible.\n"
        "Press the correct key to continue to the next trial.\n\n"
        "Press SPACE when you are ready."
    )
    show_instruction_screen(win, text, title=title, title_color=title_color)


def fit_image_preserve_aspect(image_stim):
    orig_size = getattr(image_stim, "_origSize", None)
    if not orig_size or len(orig_size) != 2:
        image_stim.size = IMAGE_BOUND_SIZE
        return

    orig_w, orig_h = orig_size
    if not orig_w or not orig_h:
        image_stim.size = IMAGE_BOUND_SIZE
        return

    max_w, max_h = IMAGE_BOUND_SIZE
    scale = min(max_w / orig_w, max_h / orig_h)
    image_stim.size = (orig_w * scale, orig_h * scale)


def draw_trial_frame(image_stim, left_label_stim, right_label_stim, error_stim=None):
    image_stim.draw()
    if error_stim is not None:
        error_stim.draw()
    left_label_stim.draw()
    right_label_stim.draw()


def run_trial(win, image_stim, fixation_stim, left_label_stim, right_label_stim, error_stim, trial):
    core, event, _, _ = require_psychopy()

    event.clearEvents(eventType="keyboard")

    fixation_stim.draw()
    left_label_stim.draw()
    right_label_stim.draw()
    win.flip()
    core.wait(FIXATION_SEC)

    event.clearEvents(eventType="keyboard")
    image_stim.image = trial["stimulus_file"]
    fit_image_preserve_aspect(image_stim)
    draw_trial_frame(image_stim, left_label_stim, right_label_stim)
    win.flip()

    timer = core.Clock()
    first_pressed_key = None
    first_rt_sec = None
    incorrect_attempts = 0
    while True:
        keys = event.getKeys(keyList=[KEY_LEFT, KEY_RIGHT] + QUIT_KEYS, timeStamped=timer)
        if not keys:
            core.wait(0.001)
            continue
        pressed_key, rt_sec = keys[0]
        if pressed_key in QUIT_KEYS:
            raise TaskInterrupted
        if first_pressed_key is None:
            first_pressed_key = pressed_key
            first_rt_sec = rt_sec
        if pressed_key == trial["correct_response"]:
            core.wait(ITI_SEC)
            return {
                "participant_response": first_pressed_key,
                "final_response": pressed_key,
                "first_rt_sec": first_rt_sec,
                "rt_sec": rt_sec,
                "final_rt_sec": rt_sec,
                "correct": int(first_pressed_key == trial["correct_response"]),
                "incorrect_attempts": incorrect_attempts,
                "correction_required": int(incorrect_attempts > 0),
            }

        incorrect_attempts += 1
        draw_trial_frame(image_stim, left_label_stim, right_label_stim, error_stim=error_stim)
        win.flip()


def build_run_setup(
    *,
    participant_last4: str,
    script_type: str,
    session_number: int | None,
    smell_order_group: str | None = None,
    task_order_group: str | None = None,
    participant_alias: str = "",
    researcher: str = "",
) -> IATRunSetup:
    participant = parse_participant_last4(participant_last4)
    if smell_order_group is None or task_order_group is None:
        assignment = resolve_participant_assignment(participant.raw_last4)
        smell_order_group = smell_order_group or assignment.smell_order_group
        task_order_group = task_order_group or assignment.task_order_group
    iat_version = assign_iat_version(participant.numeric_id)
    version_cfg = get_version_config(iat_version)

    if script_type == SCRIPT_TYPE_MAIN:
        if session_number not in (1, 2, 3):
            raise ValueError("Main IAT session_number must be 1, 2, or 3.")
        condition = smell_condition_order(smell_order_group)[session_number - 1]
        resolved_session_number = session_number
    elif script_type == SCRIPT_TYPE_PRACTICE:
        condition = CONDITION_CONTROL_NO_SMELL
        resolved_session_number = PRACTICE_SESSION_NUMBER
    else:
        raise ValueError(f"Unsupported script_type: {script_type}")

    run = RunIdentity(
        participant=participant,
        task=TASK_IAT,
        script_type=script_type,
        session_number=resolved_session_number,
        condition=condition,
        task_order_group=task_order_group,
        smell_order_group=smell_order_group,
    )
    return IATRunSetup(
        run=run,
        participant_alias=participant_alias or default_participant_alias(participant.raw_last4),
        researcher=researcher,
        iat_version=iat_version,
        version_source="auto_from_participant_last4",
        version_cfg=version_cfg,
    )


def collect_run_setup(script_type: str) -> IATRunSetup:
    _, _, gui, _ = require_psychopy()

    if script_type == SCRIPT_TYPE_PRACTICE:
        title = "SC-IAT Practice Setup"
    elif script_type == SCRIPT_TYPE_MAIN:
        title = "SC-IAT Main Setup"
    else:
        raise ValueError(f"Unsupported script_type: {script_type}")

    dlg = gui.Dlg(title=title)
    dlg.addText(
        "IAT version, smell order, and task order are assigned automatically from the participant ID and logbook."
    )
    dlg.addField("Participant ID (last 4 digits):")
    dlg.addField("Participant alias (optional):")
    dlg.addField("Researcher:")
    if script_type == SCRIPT_TYPE_MAIN:
        dlg.addField("Session number:", choices=["1", "2", "3"])
    dlg_data = dlg.show()
    if not dlg.OK:
        raise SystemExit

    participant_last4 = str(dlg_data[0]).strip()
    participant = parse_participant_last4(participant_last4)
    participant_alias = str(dlg_data[1]).strip() or default_participant_alias(participant.raw_last4)
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


def fieldnames() -> list[str]:
    return [
        "participant_id",
        "participant_code",
        "participant_numeric_id",
        "task",
        "script_type",
        "session_number",
        "condition",
        "smell_order_group",
        "task_order_group",
        "iat_version",
        "version_source",
        "order_condition",
        "side_condition",
        "task_start_time_iso",
        "timestamp",
        "trial_end_time_iso",
        "time_elapsed_ms",
        "block_number",
        "block_name",
        "block_type",
        "mapping_name",
        "trial_number_global",
        "trial_number_in_block",
        "stimulus_filename",
        "stimulus_category",
        "correct_response",
        "participant_response",
        "final_response",
        "rt_ms",
        "rt_sec",
        "correct",
        "incorrect_attempts",
        "correction_required",
    ]


def create_visual_stims(win):
    _, _, _, visual = require_psychopy()
    image_stim = visual.ImageStim(win, size=IMAGE_BOUND_SIZE, pos=(0.0, 0.0))
    fixation_stim = visual.TextStim(win, text="+", color="white", height=0.06)
    error_stim = visual.TextStim(win, text="X", color="red", height=0.18, pos=(0.0, 0.0), bold=True)
    left_label_stim = visual.TextStim(
        win,
        color="white",
        height=0.04,
        pos=(-0.50, 0.44),
        alignText="left",
        anchorHoriz="left",
        anchorVert="center",
        wrapWidth=0.46,
    )
    right_label_stim = visual.TextStim(
        win,
        color="white",
        height=0.04,
        pos=(0.50, 0.44),
        alignText="right",
        anchorHoriz="right",
        anchorVert="center",
        wrapWidth=0.46,
    )
    return image_stim, fixation_stim, error_stim, left_label_stim, right_label_stim


def build_logbook_entries(
    setup: IATRunSetup,
    *,
    out_csv: Path,
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
        iat_version=setup.iat_version,
        iat_order_condition=setup.version_cfg["order_condition"],
        iat_side_condition=setup.version_cfg["side_condition"],
        output_filename=out_csv.name,
        output_path=str(out_csv),
        status=status,
        notes=notes,
    )
    return participant_entry, run_entry


def write_iat_logbook_entry(
    setup: IATRunSetup,
    *,
    out_csv: Path,
    status: str,
    notes: str = "",
    run_timestamp: datetime | None = None,
    logbook_path: Path | None = None,
):
    participant_entry, run_entry = build_logbook_entries(
        setup,
        out_csv=out_csv,
        status=status,
        notes=notes,
        run_timestamp=run_timestamp,
    )
    return record_run(participant_entry, run_entry, logbook_path=logbook_path)


def build_rows(
    setup: IATRunSetup,
    blocks: list[dict[str, object]],
    stimulus_pools: dict[str, list[Path]],
    out_csv: Path,
) -> None:
    core, _, _, visual = require_psychopy()

    rng = random.Random()
    practice_pools = build_practice_pools(stimulus_pools)

    win = visual.Window(size=(1200, 800), fullscr=True, color=(-0.1, -0.1, -0.1), units="height")
    try:
        image_stim, fixation_stim, error_stim, left_label_stim, right_label_stim = create_visual_stims(win)
        task_start_timestamp = datetime.now()
        task_start_time_iso = task_start_timestamp.isoformat(timespec="milliseconds")
        task_clock = core.Clock()
        participant_code = format_participant_code(setup.run.participant.raw_last4)

        show_initial_instruction(win, script_type=setup.run.script_type)

        global_trial = 0
        with out_csv.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames())
            writer.writeheader()

            for block in blocks:
                left_label, right_label = labels_for_block(block)
                left_label_stim.text = left_label
                right_label_stim.text = right_label
                show_block_instruction(
                    win,
                    block,
                    left_label,
                    right_label,
                    script_type=setup.run.script_type,
                )

                block_pools = practice_pools if block["stimulus_mode"] == "fixed_subset" else stimulus_pools
                trials = build_block_trials(block, block_pools, rng)

                for trial_index, trial in enumerate(trials, start=1):
                    global_trial += 1
                    response_data = run_trial(
                        win,
                        image_stim,
                        fixation_stim,
                        left_label_stim,
                        right_label_stim,
                        error_stim,
                        trial,
                    )
                    trial_end_timestamp = datetime.now()
                    writer.writerow(
                        {
                            "participant_id": setup.run.participant.raw_last4,
                            "participant_code": participant_code,
                            "participant_numeric_id": setup.run.participant.numeric_id,
                            "task": setup.run.task,
                            "script_type": setup.run.script_type,
                            "session_number": setup.run.session_number,
                            "condition": setup.run.condition,
                            "smell_order_group": setup.run.smell_order_group,
                            "task_order_group": setup.run.task_order_group,
                            "iat_version": setup.iat_version,
                            "version_source": setup.version_source,
                            "order_condition": setup.version_cfg["order_condition"],
                            "side_condition": setup.version_cfg["side_condition"],
                            "task_start_time_iso": task_start_time_iso,
                            "timestamp": trial_end_timestamp.isoformat(timespec="seconds"),
                            "trial_end_time_iso": trial_end_timestamp.isoformat(timespec="milliseconds"),
                            "time_elapsed_ms": int(round(task_clock.getTime() * 1000)),
                            "block_number": block["block_num"],
                            "block_name": block["block_name"],
                            "block_type": block["block_type"],
                            "mapping_name": mapping_display_name(str(block["mapping_name"])),
                            "trial_number_global": global_trial,
                            "trial_number_in_block": trial_index,
                            "stimulus_filename": Path(trial["stimulus_file"]).name,
                            "stimulus_category": trial["stimulus_category"],
                            "correct_response": trial["correct_response"],
                            "participant_response": response_data["participant_response"],
                            "final_response": response_data["final_response"],
                            "rt_ms": milliseconds_from_seconds(response_data["rt_sec"]),
                            "rt_sec": round(response_data["rt_sec"], 4)
                            if response_data["rt_sec"] is not None
                            else "",
                            "correct": response_data["correct"],
                            "incorrect_attempts": response_data["incorrect_attempts"],
                            "correction_required": response_data["correction_required"],
                        }
                    )

        closing_title = (
            "PRACTICE COMPLETE" if setup.run.script_type == SCRIPT_TYPE_PRACTICE else "Task complete"
        )
        closing_color = "red" if setup.run.script_type == SCRIPT_TYPE_PRACTICE else "white"
        show_instruction_screen(
            win,
            "Your data has been saved.\n\nYou may now ask the researcher for further instructions.\n\nPress SPACE to close.",
            title=closing_title,
            title_color=closing_color,
        )
    finally:
        win.close()


def run_iat(script_type: str) -> None:
    setup = collect_run_setup(script_type)
    stimulus_pools = load_stimulus_pools()

    if script_type == SCRIPT_TYPE_PRACTICE:
        blocks = build_practice_blocks(setup.version_cfg)
    elif script_type == SCRIPT_TYPE_MAIN:
        blocks = build_main_blocks(setup.version_cfg)
    else:
        raise ValueError(f"Unsupported script_type: {script_type}")

    data_dir = TASK_DIR / "data"
    data_dir.mkdir(exist_ok=True)
    out_csv = data_dir / build_output_filename(
        setup.run,
        iat_version=setup.iat_version,
    )

    status = "completed"
    notes = ""
    pending_error: Exception | None = None

    try:
        build_rows(setup, blocks, stimulus_pools, out_csv)
    except TaskInterrupted:
        status = "interrupted"
    except Exception as exc:
        status = "invalid"
        notes = f"{type(exc).__name__}: {exc}"
        pending_error = exc

    try:
        write_iat_logbook_entry(
            setup,
            out_csv=out_csv,
            status=status,
            notes=notes,
        )
    except Exception as exc:
        if pending_error is None:
            raise
        notes = f"{notes} | logbook_write_failed={type(exc).__name__}: {exc}".strip(" |")

    if pending_error is not None:
        raise pending_error
