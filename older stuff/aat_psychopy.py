#!/usr/bin/env python3
"""
Approach-Avoidance Task (AAT) for PsychoPy.

Keyboard mapping:
- DOWN key -> pull (approach)
- UP key   -> push (avoid)

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
IMAGE_ROOT_DIR = Path("vaast images and script/shc_aat_material")
SHC_IMAGE_DIR = IMAGE_ROOT_DIR / "background_shc"
FHC_IMAGE_DIR = IMAGE_ROOT_DIR / "background_fhc"
DATA_DIR = Path("data")

FIXATION_DURATION = 0.5
MAX_RT = 3.5
ITI_MIN = 0.6
ITI_MAX = 1.0
ANIM_DURATION = 0.25
ANIM_FRAMES = 15

# Each image appears exactly once per block.
# With two opposite-mapping blocks, each image is approached once and avoided once overall.
TRIAL_REPS_PER_BLOCK = 1
WINDOW_SIZE = (1280, 800)
BG_COLOR = "black"
EXPECTED_STIMULI_PER_CATEGORY = 25

KEY_TO_ACTION = {
    "down": "approach",  # pull
    "up": "avoid",       # push
}
BUTTON_TO_ACTION = {
    "z": "approach",
    "m": "avoid",
}
QUIT_KEYS = ["escape"]
JOYSTICK_AXIS_THRESHOLD = 0.6
JOYSTICK_AXIS_NEUTRAL = 0.2
JOYSTICK_BUTTON_TO_ACTION = {
    0: "approach",
    1: "avoid",
}


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
    prev_buttons: Optional[List[int]],
) -> Tuple[Optional[str], Optional[str], bool, Optional[List[int]]]:
    if joy is None:
        return None, None, axis_armed, prev_buttons

    buttons = list(joy.getAllButtons())
    if prev_buttons is None or len(prev_buttons) != len(buttons):
        prev_buttons = [0] * len(buttons)

    # Trigger only on button down transition.
    for idx, state in enumerate(buttons):
        if state and not prev_buttons[idx] and idx in JOYSTICK_BUTTON_TO_ACTION:
            return f"joy_button_{idx}", JOYSTICK_BUTTON_TO_ACTION[idx], axis_armed, buttons

    # Axis pull/push response (Y axis): down = approach, up = avoid.
    y = joy.getY()
    if abs(y) < JOYSTICK_AXIS_NEUTRAL:
        axis_armed = True
    if axis_armed and y <= -JOYSTICK_AXIS_THRESHOLD:
        return "joy_axis_down", "approach", False, buttons
    if axis_armed and y >= JOYSTICK_AXIS_THRESHOLD:
        return "joy_axis_up", "avoid", False, buttons

    return None, None, axis_armed, buttons


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
    image_stim = visual.ImageStim(win, image=None, size=(0.6, 0.6))
    joy = setup_joystick()
    stimuli = discover_stimuli(SHC_IMAGE_DIR, FHC_IMAGE_DIR)
    blocks = get_block_mapping(counterbalance_condition)
    total_trials = len(stimuli) * TRIAL_REPS_PER_BLOCK * len(blocks)
    if total_trials != 100:
        raise RuntimeError(f"Task misconfigured: expected 100 total trials, got {total_trials}.")

    show_text_and_wait(
        win,
        "In this task, you can respond with the keyboard, buttons, or joystick.\n"
        "You should approach stimuli with the DOWN key, the Z key, joystick movement forward, "
        "or joystick button 0.\n"
        "You should avoid stimuli with the UP key, the M key, joystick movement backward, "
        "or joystick button 1.\n\n"
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
            f"Block {block_idx}/{len(blocks)}: {block['name']}\n\n"
            "In this block, your instructions are to approach "
            f"{', '.join(approach_cats)} stimuli by moving the joystick forward, "
            "pressing the DOWN key, pressing the Z key, or pressing joystick button 0.\n"
            "In this block, your instructions are to avoid "
            f"{', '.join(avoid_cats)} stimuli by moving the joystick backward, "
            "pressing the UP key, pressing the M key, or pressing joystick button 1.\n\n"
            "Press SPACE to begin this block.",
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
            prev_buttons = list(joy.getAllButtons()) if joy is not None else None

            while clock.getTime() < MAX_RT:
                quit_if_requested()
                image_stim.draw()
                win.flip()
                keys = event.getKeys(
                    keyList=list(KEY_TO_ACTION.keys()) + list(BUTTON_TO_ACTION.keys()) + QUIT_KEYS,
                    timeStamped=clock,
                )
                if keys:
                    key, t = keys[0]
                    if key in QUIT_KEYS:
                        core.quit()
                    responded_key = key
                    responded_source = "keyboard_button" if key in BUTTON_TO_ACTION else "keyboard_arrow"
                    responded_action = KEY_TO_ACTION.get(key) or BUTTON_TO_ACTION.get(key)
                    rt = t
                    break

                joy_key, joy_action, axis_armed, prev_buttons = _poll_joystick_action(
                    joy, axis_armed, prev_buttons
                )
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
