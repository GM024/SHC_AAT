"""
Single-Category IAT (SC-IAT): SHC with Disease vs Danger attributes
with within-IAT counterbalancing by iat_version.

Run:
    python iat_psychopy.py
"""

import csv
import random
from datetime import datetime
from pathlib import Path

from psychopy import core, event, gui, visual


# =====================================================================
# STIMULUS FOLDERS / PATTERNS (edit here)
# =====================================================================
SCRIPT_DIR = Path(__file__).resolve().parent


def resolve_stim_root():
    candidates = [
        SCRIPT_DIR / "material",
        SCRIPT_DIR.parent / "material",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def resolve_existing_dir(candidates, label):
    for candidate in candidates:
        if candidate.exists():
            return candidate
    candidate_text = "\n".join(str(candidate) for candidate in candidates)
    raise RuntimeError(f"Could not locate {label}. Checked:\n{candidate_text}")


def resolve_shc_dir(stim_root: Path):
    candidates = [
        stim_root / "background_shc",
        stim_root / "background_SHC",
        stim_root / "shc_aat_material" / "background_shc",
        stim_root / "shc_aat_material" / "background_SHC",
    ]
    return resolve_existing_dir(candidates, "SHC stimulus folder")


def resolve_dirti_dir(stim_root: Path):
    candidates = [
        stim_root / "DIRTI_database" / "DIRTI Database",
        stim_root / "DIRTI Database",
        stim_root / "danger" / "DIRTI_database" / "DIRTI Database",
        stim_root / "danger" / "DIRTI Database",
    ]
    return resolve_existing_dir(candidates, "DIRTI stimulus folder")


STIM_ROOT = resolve_stim_root()

# SHC images
SHC_DIR = resolve_shc_dir(STIM_ROOT)

# DIRTI source folder used for both attribute categories
DIRTI_DIR = resolve_dirti_dir(STIM_ROOT)

# File-name patterns used to split DIRTI into attribute categories.
DISEASE_PATTERNS = ["*injuries_infections*.jpg", "*hygiene*.jpg", "*body products*.jpg"]
DANGER_PATTERNS = ["*death*.jpg"]

VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff"}


# =====================================================================
# TRIAL COUNTS (edit here)
# =====================================================================
TRIALS_BLOCK_1 = 24   # Practice 1: Disease vs Danger
TRIALS_BLOCK_2 = 24   # Combined practice
TRIALS_BLOCK_3 = 72   # Combined test
TRIALS_BLOCK_4 = 24   # Reversed combined practice
TRIALS_BLOCK_5 = 72   # Reversed combined test


# =====================================================================
# TIMING PARAMETERS (edit here)
# =====================================================================
FIXATION_SEC = 0.30
ITI_SEC = 0.15


# =====================================================================
# TASK SETTINGS
# =====================================================================
KEY_LEFT = "e"
KEY_RIGHT = "i"
QUIT_KEYS = ["escape"]

CAT_SHC = "SHC"
CAT_DISEASE = "Disease"
CAT_DANGER = "Danger"


def load_stimuli(folder: Path):
    if not folder.exists():
        raise RuntimeError(f"Stimulus folder does not exist: {folder}")
    files = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in VALID_EXTENSIONS]
    if not files:
        raise RuntimeError(f"No valid image files found in: {folder}")
    return sorted(files)


def load_stimuli_from_patterns(folder: Path, patterns):
    if not folder.exists():
        raise RuntimeError(f"Stimulus folder does not exist: {folder}")
    files = []
    for pattern in patterns:
        files.extend(
            [p for p in folder.glob(pattern) if p.is_file() and p.suffix.lower() in VALID_EXTENSIONS]
        )
    unique_files = sorted(set(files))
    if not unique_files:
        raise RuntimeError(f"No files found for patterns {patterns} in: {folder}")
    return unique_files


def get_version_config(iat_version):
    version_map = {
        1: {"order_condition": "disease_first", "side_condition": "combined_left"},
        2: {"order_condition": "disease_first", "side_condition": "combined_right"},
        3: {"order_condition": "danger_first", "side_condition": "combined_left"},
        4: {"order_condition": "danger_first", "side_condition": "combined_right"},
    }
    if iat_version not in version_map:
        raise ValueError("iat_version must be 1, 2, 3, or 4.")
    cfg = version_map[iat_version]
    cfg["iat_version"] = iat_version
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


def auto_assign_iat_version(participant_id_num):
    """Assign version using repeating 1-4 cycle based on numeric participant ID."""
    if participant_id_num < 1:
        raise ValueError("participant_id must be >= 1.")
    return ((participant_id_num - 1) % 4) + 1


def mapping_recipe(mapping_name, side_condition):
    # side_condition controls where the combined category appears.
    if mapping_name == "shc_disease_vs_danger":
        if side_condition == "combined_left":
            return {CAT_SHC: KEY_LEFT, CAT_DISEASE: KEY_LEFT, CAT_DANGER: KEY_RIGHT}
        return {CAT_DANGER: KEY_LEFT, CAT_SHC: KEY_RIGHT, CAT_DISEASE: KEY_RIGHT}

    if mapping_name == "shc_danger_vs_disease":
        if side_condition == "combined_left":
            return {CAT_SHC: KEY_LEFT, CAT_DANGER: KEY_LEFT, CAT_DISEASE: KEY_RIGHT}
        return {CAT_DISEASE: KEY_LEFT, CAT_SHC: KEY_RIGHT, CAT_DANGER: KEY_RIGHT}

    raise ValueError(f"Unknown mapping_name: {mapping_name}")


def attribute_practice_recipe(first_combined_mapping, side_condition):
    # Practice 1 follows the attribute side setup that matches Block 2.
    if first_combined_mapping == "shc_disease_vs_danger":
        if side_condition == "combined_left":
            return {CAT_DISEASE: KEY_LEFT, CAT_DANGER: KEY_RIGHT}
        return {CAT_DANGER: KEY_LEFT, CAT_DISEASE: KEY_RIGHT}
    if side_condition == "combined_left":
        return {CAT_DANGER: KEY_LEFT, CAT_DISEASE: KEY_RIGHT}
    return {CAT_DISEASE: KEY_LEFT, CAT_DANGER: KEY_RIGHT}


def build_blocks(version_cfg):
    first_map = version_cfg["first_combined_mapping"]
    second_map = version_cfg["second_combined_mapping"]
    side = version_cfg["side_condition"]

    blocks = [
        {
            "block_num": 1,
            "block_name": "Practice 1",
            "block_type": "practice",
            "mapping_name": "Disease vs Danger",
            "n_trials": TRIALS_BLOCK_1,
            "trial_recipe": attribute_practice_recipe(first_map, side),
        },
        {
            "block_num": 2,
            "block_name": "Combined practice",
            "block_type": "practice",
            "mapping_name": first_map,
            "n_trials": TRIALS_BLOCK_2,
            "trial_recipe": mapping_recipe(first_map, side),
        },
        {
            "block_num": 3,
            "block_name": "Combined test",
            "block_type": "test",
            "mapping_name": first_map,
            "n_trials": TRIALS_BLOCK_3,
            "trial_recipe": mapping_recipe(first_map, side),
        },
        {
            "block_num": 4,
            "block_name": "Reversed combined practice",
            "block_type": "practice",
            "mapping_name": second_map,
            "n_trials": TRIALS_BLOCK_4,
            "trial_recipe": mapping_recipe(second_map, side),
        },
        {
            "block_num": 5,
            "block_name": "Reversed combined test",
            "block_type": "test",
            "mapping_name": second_map,
            "n_trials": TRIALS_BLOCK_5,
            "trial_recipe": mapping_recipe(second_map, side),
        },
    ]
    return blocks


def build_block_trials(block, stimulus_pools):
    recipe = block["trial_recipe"]  # category -> correct key
    categories = list(recipe.keys())
    n_categories = len(categories)
    n_trials = block["n_trials"]

    base_n = n_trials // n_categories
    remainder = n_trials % n_categories

    counts = {cat: base_n for cat in categories}
    for cat in random.sample(categories, remainder):
        counts[cat] += 1

    trials = []
    for cat in categories:
        for _ in range(counts[cat]):
            trials.append(
                {
                    "stimulus_category": cat,
                    "stimulus_file": str(random.choice(stimulus_pools[cat])),
                    "correct_response": recipe[cat],
                }
            )

    random.shuffle(trials)
    return trials


def labels_for_block(block):
    recipe = block["trial_recipe"]
    left_cats = [cat for cat, key in recipe.items() if key == KEY_LEFT]
    right_cats = [cat for cat, key in recipe.items() if key == KEY_RIGHT]
    left_label = f"LEFT ({KEY_LEFT.upper()}): " + " + ".join(left_cats)
    right_label = f"RIGHT ({KEY_RIGHT.upper()}): " + " + ".join(right_cats)
    return left_label, right_label


def mapping_display_name(mapping_name):
    if mapping_name == "shc_disease_vs_danger":
        return "SHC + Disease vs Danger"
    if mapping_name == "shc_danger_vs_disease":
        return "SHC + Danger vs Disease"
    return mapping_name


def show_instruction(win, text):
    txt = visual.TextStim(win, text=text, color="white", height=0.035, wrapWidth=1.5)
    txt.draw()
    win.flip()
    keys = event.waitKeys(keyList=["space"] + QUIT_KEYS)
    if keys and keys[0] in QUIT_KEYS:
        core.quit()


def run_trial(win, image_stim, fixation_stim, left_label_stim, right_label_stim, error_stim, trial):
    # Clear any carry-over keypresses from previous trials/instruction screens.
    event.clearEvents(eventType="keyboard")

    fixation_stim.draw()
    left_label_stim.draw()
    right_label_stim.draw()
    win.flip()
    core.wait(FIXATION_SEC)

    # Start response collection from a clean state at stimulus onset.
    event.clearEvents(eventType="keyboard")
    image_stim.image = trial["stimulus_file"]
    image_stim.draw()
    left_label_stim.draw()
    right_label_stim.draw()
    win.flip()

    timer = core.Clock()
    while True:
        keys = event.getKeys(keyList=[KEY_LEFT, KEY_RIGHT] + QUIT_KEYS, timeStamped=timer)
        if not keys:
            continue
        pressed_key, rt_sec = keys[0]
        if pressed_key in QUIT_KEYS:
            core.quit()
        if pressed_key == trial["correct_response"]:
            core.wait(ITI_SEC)
            return pressed_key, rt_sec, 1

        error_stim.draw()
        left_label_stim.draw()
        right_label_stim.draw()
        win.flip()
        event.waitKeys(keyList=[trial["correct_response"]] + QUIT_KEYS)
        core.wait(ITI_SEC)
        return pressed_key, rt_sec, 0


def main():
    random.seed()

    stimuli = {
        CAT_SHC: load_stimuli(SHC_DIR),
        CAT_DISEASE: load_stimuli_from_patterns(DIRTI_DIR, DISEASE_PATTERNS),
        CAT_DANGER: load_stimuli_from_patterns(DIRTI_DIR, DANGER_PATTERNS),
    }

    dlg = gui.Dlg(title="SC-IAT Setup")
    dlg.addText("Task version is assigned automatically from Participant ID.")
    dlg.addField("Participant ID:")
    dlg_data = dlg.show()
    if not dlg.OK:
        return

    participant_id_raw = str(dlg_data[0]).strip()

    try:
        participant_id = int(participant_id_raw)
        iat_version = auto_assign_iat_version(participant_id)
        version_source = "auto_from_participant_id"
    except Exception:
        raise RuntimeError("Participant ID must be a numeric integer >= 1.")

    version_cfg = get_version_config(iat_version)

    blocks = build_blocks(version_cfg)

    data_dir = Path(__file__).resolve().parent / "data"
    data_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_csv = data_dir / f"sciat_{participant_id}_v{iat_version}_{ts}.csv"

    win = visual.Window(size=(1200, 800), fullscr=False, color=(-0.1, -0.1, -0.1), units="height")
    image_stim = visual.ImageStim(win, size=(0.55, 0.55), pos=(0.0, 0.0))
    fixation_stim = visual.TextStim(win, text="+", color="white", height=0.06)
    error_stim = visual.TextStim(win, text="X", color="red", height=0.12, pos=(0.0, -0.2))
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

    show_instruction(
        win,
        f"You will categorize images using two keys.\n\n"
        "In this task, SHC stands for Second-hand clothing.\n\n"
        f"Press '{KEY_LEFT.upper()}' for the left category and '{KEY_RIGHT.upper()}' for the right category.\n"
        "Respond as quickly and accurately as possible.\n"
        "If you make an incorrect response, a red X will appear and remain on the screen until you press the correct key.\n\n"
        "Press SPACE to start.",
    )

    fieldnames = [
        "participant_id",
        "iat_version",
        "version_source",
        "order_condition",
        "side_condition",
        "timestamp",
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
        "rt_sec",
        "correct",
    ]

    global_trial = 0
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for block in blocks:
            left_label, right_label = labels_for_block(block)
            left_label_stim.text = left_label
            right_label_stim.text = right_label

            show_instruction(
                win,
                f"{block['block_name']} ({block['block_type']})\n\n"
                f"Mapping: {mapping_display_name(block['mapping_name'])}\n\n"
                f"Press '{KEY_LEFT.upper()}' for {left_label.replace(chr(10), ' ')}.\n"
                f"Press '{KEY_RIGHT.upper()}' for {right_label.replace(chr(10), ' ')}.\n\n"
                "If you respond incorrectly, a red X will stay visible until you press the correct key.\n\n"
                "Press SPACE when you are ready.",
            )

            trials = build_block_trials(block, stimuli)
            for t_idx, trial in enumerate(trials, start=1):
                global_trial += 1
                pressed_key, rt_sec, correct = run_trial(
                    win,
                    image_stim,
                    fixation_stim,
                    left_label_stim,
                    right_label_stim,
                    error_stim,
                    trial,
                )

                writer.writerow(
                    {
                        "participant_id": participant_id,
                        "iat_version": version_cfg["iat_version"],
                        "version_source": version_source,
                        "order_condition": version_cfg["order_condition"],
                        "side_condition": version_cfg["side_condition"],
                        "timestamp": datetime.now().isoformat(timespec="seconds"),
                        "block_number": block["block_num"],
                        "block_name": block["block_name"],
                        "block_type": block["block_type"],
                        "mapping_name": mapping_display_name(block["mapping_name"]),
                        "trial_number_global": global_trial,
                        "trial_number_in_block": t_idx,
                        "stimulus_filename": Path(trial["stimulus_file"]).name,
                        "stimulus_category": trial["stimulus_category"],
                        "correct_response": trial["correct_response"],
                        "participant_response": pressed_key,
                        "rt_sec": round(rt_sec, 4) if rt_sec is not None else "",
                        "correct": correct,
                    }
                )

    show_instruction(
        win,
        "Task complete.\n\nYour data has been saved.\n\nYou may now ask the researcher for further instructions.\n\nPress SPACE to close.",
    )
    win.close()
    core.quit()


if __name__ == "__main__":
    main()
