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

Data are saved in ./data as wide-text (.csv) and PsychoPy .psydat.
"""

from __future__ import annotations

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
MAX_RT = 3.5
ITI_MIN = 0.6
ITI_MAX = 1.0
ANIM_DURATION = 0.25
ANIM_FRAMES = 15
PRACTICE_TRIALS_PER_CATEGORY = 4

# Each image appears exactly once per block.
# With two opposite-mapping blocks, each image is approached once and avoided once overall.
TRIAL_REPS_PER_BLOCK = 1
WINDOW_SIZE = (1280, 800)
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
                    "image_path": str(p),
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
        "SHC": "Second-hand clothing (SHC)",
        "FHC": "First-hand clothing (FHC)",
    }
    return labels.get(code, code)


def animate_response(
    win: visual.Window,
    stim: visual.ImageStim,
    action: str,
) -> None:
    start_size = 0.6
    end_size = 1.0 if action == "approach" else 0.3

    for frame in range(ANIM_FRAMES):
        t = frame / max(1, ANIM_FRAMES - 1)
        size = start_size + (end_size - start_size) * t
        stim.size = (size, size)
        stim.draw()
        win.flip()

    core.wait(max(0.0, ANIM_DURATION - ANIM_FRAMES * (1 / 60.0)))


def show_text_and_wait(win: visual.Window, text: str, key_list=None) -> List[str]:
    msg = visual.TextStim(
        win,
        text=text,
        color="white",
        wrapWidth=1.4,
        height=0.05,
    )
    msg.draw()
    win.flip()
    keys = event.waitKeys(keyList=key_list)
    return keys or []


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

        image_stim.image = trial["image_path"]
        image_stim.size = (0.6, 0.6)
        required_action = mapping[trial["category"]]

        event.clearEvents(eventType="keyboard")
        axis_armed = abs(joy.getY()) < JOYSTICK_AXIS_NEUTRAL if joy is not None else True
        show_error = False

        while True:
            quit_if_requested()
            image_stim.draw()
            if show_error:
                error_stim.draw()
            win.flip()

            responded_key = None
            responded_action = None
            keys = event.getKeys(keyList=list(BUTTON_TO_ACTION.keys()) + QUIT_KEYS)
            if keys:
                key = keys[0]
                if key in QUIT_KEYS:
                    core.quit()
                responded_key = key
                responded_action = BUTTON_TO_ACTION.get(key)
            else:
                joy_key, joy_action, axis_armed = _poll_joystick_action(joy, axis_armed)
                if joy_key is not None:
                    responded_key = joy_key
                    responded_action = joy_action

            if responded_key is None:
                continue

            if responded_action == required_action:
                animate_response(win, image_stim, responded_action)
                break

            # Practice-only correction feedback: keep the red X visible until correct.
            show_error = True


def main() -> None:
    exp_name = "AAT_PsychoPy"
    exp_info = {
        "participant": "001",
        "session": "001",
    }

    dlg = gui.DlgFromDict(exp_info, title=exp_name)
    if not dlg.OK:
        return

    participant_digits = re.sub(r"\D", "", exp_info["participant"])
    participant_number = int(participant_digits) if participant_digits else 1
    counterbalance_condition = "A" if participant_number % 2 == 0 else "B"

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    filename_base = DATA_DIR / f"{exp_info['participant']}_{exp_name}_{data.getDateStr()}"
    this_exp = data.ExperimentHandler(
        name=exp_name,
        version="1.0",
        extraInfo={**exp_info, "counterbalance": counterbalance_condition},
        runtimeInfo=None,
        dataFileName=str(filename_base),
    )

    win = visual.Window(
        size=WINDOW_SIZE,
        fullscr=False,
        color=BG_COLOR,
        units="height",
    )

    fixation = visual.TextStim(win, text="+", color="white", height=0.08)
    error_stim = visual.TextStim(win, text="X", color="red", height=0.16, bold=True)
    image_stim = visual.ImageStim(win, image=None, size=(0.6, 0.6))
    joy = setup_joystick()
    stimuli = discover_stimuli(SHC_IMAGE_DIR, FHC_IMAGE_DIR)
    practice_trials = build_practice_trials(stimuli, PRACTICE_TRIALS_PER_CATEGORY)
    blocks = get_block_mapping(counterbalance_condition)
    total_trials = len(stimuli) * TRIAL_REPS_PER_BLOCK * len(blocks)
    if total_trials != 100:
        raise RuntimeError(f"Task misconfigured: expected 100 total trials, got {total_trials}.")

    show_text_and_wait(
        win,
        "In this task, respond primarily with joystick movement.\n"
        "Move the joystick forward to approach and backward to avoid.\n"
        "If needed, use keyboard backup keys: Q = approach, M = avoid.\n\n"
        "Before each real block, there is a short practice block.\n"
        "In practice only: if your response is incorrect, a red X appears and stays until "
        "you make the correct response.\n"
        "In the real blocks, no red X feedback is shown.\n\n"
        "Please respond as quickly and accurately as possible.\n"
        "Press SPACE to start.",
        key_list=["space"],
    )

    global_trial_index = 0

    for block_idx, block in enumerate(blocks, start=1):
        mapping = block["mapping"]
        approach_cats = [category_label(k) for k, v in mapping.items() if v == "approach"]
        avoid_cats = [category_label(k) for k, v in mapping.items() if v == "avoid"]

        show_text_and_wait(
            win,
            f"Practice before Block {block_idx}/{len(blocks)}: {block['name']}\n\n"
            "In this block, your instructions are to approach "
            f"{', '.join(approach_cats)} stimuli by moving the joystick forward, "
            "or pressing Q as backup.\n"
            "In this block, your instructions are to avoid "
            f"{', '.join(avoid_cats)} stimuli by moving the joystick backward, "
            "or pressing M as backup.\n\n"
            "Practice feedback rule: if you respond incorrectly, a red X appears and stays "
            "until you perform the correct action.\n\n"
            "Press SPACE to begin practice.",
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
        show_text_and_wait(
            win,
            f"Practice complete.\n\nNow Block {block_idx}/{len(blocks)}: {block['name']} will start.\n"
            "In this real block, no red X feedback will be shown.\n\n"
            "Press SPACE to begin.",
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

            image_stim.image = trial["image_path"]
            image_stim.size = (0.6, 0.6)

            # Ignore any input made before stimulus onset.
            event.clearEvents(eventType="keyboard")
            clock = core.Clock()
            responded_key = None
            responded_source = None
            responded_action = None
            rt = None
            axis_armed = (
                abs(joy.getY()) < JOYSTICK_AXIS_NEUTRAL if joy is not None else True
            )

            while clock.getTime() < MAX_RT:
                quit_if_requested()
                image_stim.draw()
                win.flip()
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
                    rt = t
                    break

                joy_key, joy_action, axis_armed = _poll_joystick_action(joy, axis_armed)
                if joy_key is not None:
                    responded_key = joy_key
                    responded_source = "joystick"
                    responded_action = joy_action
                    rt = clock.getTime()
                    break

            required_action = mapping[trial["category"]]
            response_action = responded_action
            correct = int(response_action == required_action)

            if responded_key is not None:
                animate_response(win, image_stim, response_action)

            core.wait(ITI_MIN + (ITI_MAX - ITI_MIN) * (trial_idx % 5) / 4.0)

            # Log trial data
            trial_handler.addData("participant", exp_info["participant"])
            trial_handler.addData("session", exp_info["session"])
            trial_handler.addData("counterbalance", counterbalance_condition)
            trial_handler.addData("block_number", block_idx)
            trial_handler.addData("block_name", block["name"])
            trial_handler.addData("trial_in_block", trial_idx)
            trial_handler.addData("trial_global", global_trial_index)
            trial_handler.addData("image_name", trial["image_name"])
            trial_handler.addData("image_path", trial["image_path"])
            trial_handler.addData("category", trial["category"])
            trial_handler.addData("stimulus_number", trial["stimulus_number"])
            trial_handler.addData("clothing_type", trial["clothing_type"])
            trial_handler.addData("required_action", required_action)
            trial_handler.addData("response_key", responded_key)
            trial_handler.addData("response_source", responded_source)
            trial_handler.addData("response_action", response_action)
            trial_handler.addData("correct", correct)
            trial_handler.addData("rt", rt)
            this_exp.nextEntry()

        show_text_and_wait(
            win,
            f"End of block {block_idx}.\n\nPress SPACE to continue.",
            key_list=["space"],
        )

    show_text_and_wait(
        win,
        "Task complete.\n\nThank you!\nPress SPACE to exit.",
        key_list=["space"],
    )

    this_exp.saveAsWideText(str(filename_base) + ".csv")
    this_exp.saveAsPickle(str(filename_base))

    win.close()
    core.quit()


if __name__ == "__main__":
    main()
