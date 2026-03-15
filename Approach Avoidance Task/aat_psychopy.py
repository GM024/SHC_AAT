#!/usr/bin/env python3
"""
Approach-Avoidance Task (AAT) for PsychoPy.

Keyboard backup mapping:
- Q key -> approach
- M key -> avoid

Default categories (auto-discovered from filenames):
- shc*.png -> SHC
- fhc*.png -> FHC

Block design (counterbalanced by participant number parity):
- Congruent: approach SHC, avoid FHC
- Incongruent: approach FHC, avoid SHC

Data are saved in ./data as raw and cleaned .csv files.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from psychopy import core, data, event, gui, visual
from psychopy.hardware import joystick


# -----------------------------
# Configuration
# -----------------------------
PROJECT_DIR = Path(__file__).resolve().parent
DATA_DIR = PROJECT_DIR / "data"
INTERNAL_DATA_DIR = DATA_DIR / "psychopy_internal"


def resolve_image_root_dir() -> Path:
    # Support both the original folder name and the current material folder.
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
    "session",
    "counterbalance",
    "block_number",
    "block_name",
    "trial_in_block",
    "trial_global",
    "category",
    "stimulus_number",
    "clothing_type",
    "required_action",
    "correct",
    "first_rt",
    "final_rt",
    "incorrect_attempts",
    "correction_required",
    "task_duration_s",
]

# Each image appears exactly once per block.
# With two opposite-mapping blocks, each image is approached once and avoided once overall.
TRIAL_REPS_PER_BLOCK = 1
WINDOW_SIZE = (1280, 800)
FULLSCREEN = True
BG_COLOR = "black"
EXPECTED_STIMULI_PER_CATEGORY = 25

BUTTON_TO_ACTION = {
    "q": "approach",
    "m": "avoid",
}
QUIT_KEYS = ["escape"]
JOYSTICK_AXIS_THRESHOLD = 0.6
JOYSTICK_AXIS_NEUTRAL = 0.2


def quit_if_requested() -> None:
    if event.getKeys(keyList=QUIT_KEYS):
        core.quit()


def setup_joystick() -> Optional[joystick.Joystick]:
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

    # Axis pull/push response (Y axis): down = approach, up = avoid.
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
        for p in sorted(folder.glob("*")):
            if not p.is_file() or p.suffix.lower() not in valid_ext:
                continue
            name = p.stem.lower()
            if not re.match(pattern, name):
                continue
            number = int(re.sub(r"^\D+", "", name))
            trials.append(
                {
                    "image_name": p.name,
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

    # Ensure matched SHC/FHC numbered pairs (e.g., shc7 and fhc7).
    shc_numbers = {t["stimulus_number"] for t in trials if t["category"] == "SHC"}
    fhc_numbers = {t["stimulus_number"] for t in trials if t["category"] == "FHC"}
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
    msg = visual.TextStim(
        win,
        text=text,
        color="white",
        wrapWidth=INSTRUCTION_WRAP_WIDTH,
        height=INSTRUCTION_TEXT_HEIGHT,
    )
    msg.draw()
    win.flip()
    keys = event.waitKeys(keyList=key_list)
    return keys or []


def show_formatted_text_and_wait(
    win: visual.Window,
    lines: List[Tuple[str, bool]],
    key_list=None,
) -> List[str]:
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
    keys = event.waitKeys(keyList=key_list)
    return keys or []


def save_clean_trial_data(rows: List[Dict[str, object]], output_path: Path) -> None:
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CLEAN_DATA_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in CLEAN_DATA_COLUMNS})


def build_practice_trials(
    stimuli: List[Dict[str, str]],
    trials_per_category: int,
) -> List[Dict[str, str]]:
    shc_trials = sorted(
        [t for t in stimuli if t["category"] == "SHC"],
        key=lambda t: t["stimulus_number"],
    )[:trials_per_category]
    fhc_trials = sorted(
        [t for t in stimuli if t["category"] == "FHC"],
        key=lambda t: t["stimulus_number"],
    )[:trials_per_category]

    practice_trials: List[Dict[str, str]] = []
    for i in range(max(len(shc_trials), len(fhc_trials))):
        if i < len(shc_trials):
            practice_trials.append(shc_trials[i])
        if i < len(fhc_trials):
            practice_trials.append(fhc_trials[i])
    return practice_trials


def collect_response_until_correct(
    win: visual.Window,
    image_stim: visual.ImageStim,
    error_stim: visual.TextStim,
    joy: Optional[joystick.Joystick],
    required_action: str,
) -> Dict[str, Optional[object]]:
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
            key, t = keys[0]
            if key in QUIT_KEYS:
                core.quit()
            responded_key = key
            responded_source = "keyboard_button"
            responded_action = BUTTON_TO_ACTION.get(key)
            responded_rt = t
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


def run_practice_block(
    win: visual.Window,
    fixation: visual.TextStim,
    image_stim: visual.ImageStim,
    error_stim: visual.TextStim,
    joy: Optional[joystick.Joystick],
    mapping: Dict[str, str],
    practice_trials: List[Dict[str, str]],
) -> None:
    trial_handler = data.TrialHandler(practice_trials, nReps=1, method="random")

    for trial in trial_handler:
        quit_if_requested()
        fixation.draw()
        win.flip()
        core.wait(FIXATION_DURATION)

        set_image_stimulus(image_stim, stimulus_file_path(trial))
        required_action = mapping[trial["category"]]
        collect_response_until_correct(
            win=win,
            image_stim=image_stim,
            error_stim=error_stim,
            joy=joy,
            required_action=required_action,
        )


def main() -> None:
    exp_name = "AAT_PsychoPy"
    dlg = gui.Dlg(title="AAT Setup")
    dlg.addText("Task version is assigned automatically from Participant ID.")
    dlg.addField("Participant ID:", initial="001")
    if hasattr(dlg, "requiredMsg"):
        dlg.requiredMsg.hide()
    dlg_data = dlg.show()
    if not dlg.OK:
        return

    exp_info = {
        "participant": str(dlg_data[0]).strip(),
        "session": "001",
    }

    participant_digits = re.sub(r"\D", "", exp_info["participant"])
    participant_number = int(participant_digits) if participant_digits else 1
    counterbalance_condition = "A" if participant_number % 2 == 0 else "B"

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    INTERNAL_DATA_DIR.mkdir(parents=True, exist_ok=True)

    filename_base = DATA_DIR / f"{exp_info['participant']}_{exp_name}_{data.getDateStr()}"
    internal_filename_base = INTERNAL_DATA_DIR / filename_base.name
    this_exp = data.ExperimentHandler(
        name=exp_name,
        version="1.0",
        extraInfo={**exp_info, "counterbalance": counterbalance_condition},
        runtimeInfo=None,
        savePickle=False,
        saveWideText=False,
        dataFileName=str(internal_filename_base),
    )

    win = visual.Window(
        size=WINDOW_SIZE,
        fullscr=FULLSCREEN,
        color=BG_COLOR,
        units="height",
    )
    task_clock = core.Clock()

    fixation = visual.TextStim(win, text="+", color="white", height=0.08)
    error_stim = visual.TextStim(win, text="X", color="red", height=0.16, bold=True)
    image_stim = visual.ImageStim(win, image=None, size=(IMAGE_BASE_MAX_DIM, IMAGE_BASE_MAX_DIM))
    joy = setup_joystick()
    stimuli = discover_stimuli(SHC_IMAGE_DIR, FHC_IMAGE_DIR)
    practice_trials = build_practice_trials(stimuli, PRACTICE_TRIALS_PER_CATEGORY)
    blocks = get_block_mapping(counterbalance_condition)
    cleaned_rows: List[Dict[str, object]] = []
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
        "Before each test block, you will complete a short practice block.\n"
        "If you respond incorrectly, an X will appear while the picture remains\n"
        "visible on the screen.\n"
        "You cannot continue to the next trial until you make the correct\n"
        "response. The trial will continue as soon as you respond correctly.\n"
        "This rule applies to both practice and test blocks.\n\n"
        "Please respond as quickly and accurately as possible.\n"
        "Press SPACE to start.",
        key_list=["space"],
    )

    global_trial_index = 0

    for block_idx, block in enumerate(blocks, start=1):
        mapping = block["mapping"]
        approach_cats = [category_label(k) for k, v in mapping.items() if v == "approach"]
        avoid_cats = [category_label(k) for k, v in mapping.items() if v == "avoid"]

        show_formatted_text_and_wait(
            win,
            [
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
            ],
            key_list=["space"],
        )
        run_practice_block(
            win=win,
            fixation=fixation,
            image_stim=image_stim,
            error_stim=error_stim,
            joy=joy,
            mapping=mapping,
            practice_trials=practice_trials,
        )
        show_formatted_text_and_wait(
            win,
            [
                ("Practice complete.", False),
                ("", False),
                (f"Now Block: {block['name']} will begin.", True),
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
            ],
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

            required_action = mapping[trial["category"]]
            response_data = collect_response_until_correct(
                win=win,
                image_stim=image_stim,
                error_stim=error_stim,
                joy=joy,
                required_action=required_action,
            )

            # Log trial data
            trial_handler.addData("participant", exp_info["participant"])
            trial_handler.addData("session", exp_info["session"])
            trial_handler.addData("counterbalance", counterbalance_condition)
            trial_handler.addData("block_number", block_idx)
            trial_handler.addData("block_name", block["name"])
            trial_handler.addData("trial_in_block", trial_idx)
            trial_handler.addData("trial_global", global_trial_index)
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
            trial_handler.addData("first_rt", response_data["first_rt"])
            trial_handler.addData("final_response_key", response_data["final_response_key"])
            trial_handler.addData("final_response_source", response_data["final_response_source"])
            trial_handler.addData("final_response_action", response_data["final_response_action"])
            trial_handler.addData("final_rt", response_data["final_rt"])
            trial_handler.addData("incorrect_attempts", response_data["incorrect_attempts"])
            trial_handler.addData("correction_required", response_data["correction_required"])

            cleaned_rows.append(
                {
                    "participant": exp_info["participant"],
                    "session": exp_info["session"],
                    "counterbalance": counterbalance_condition,
                    "block_number": block_idx,
                    "block_name": block["name"],
                    "trial_in_block": trial_idx,
                    "trial_global": global_trial_index,
                    "category": trial["category"],
                    "stimulus_number": trial["stimulus_number"],
                    "clothing_type": trial["clothing_type"],
                    "required_action": required_action,
                    "correct": response_data["correct"],
                    "first_rt": response_data["first_rt"],
                    "final_rt": response_data["final_rt"],
                    "incorrect_attempts": response_data["incorrect_attempts"],
                    "correction_required": response_data["correction_required"],
                }
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

    task_duration_s = task_clock.getTime()
    this_exp.extraInfo["task_duration_s"] = task_duration_s
    for row in cleaned_rows:
        row["task_duration_s"] = task_duration_s

    this_exp.saveAsWideText(str(filename_base) + ".csv")
    save_clean_trial_data(cleaned_rows, Path(str(filename_base) + "_cleaned.csv"))

    win.close()
    core.quit()


if __name__ == "__main__":
    main()
