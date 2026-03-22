# PsychoPy AAT Task Guide (Plain Language)

This folder contains a split **Approach-Avoidance Task (AAT)** workflow about clothing images:

- `AAT Task Script/aat_practice.py`: dedicated practice run
- `AAT Task Script/aat_main.py`: dedicated main run
- `AAT Task Script/aat_core.py`: shared task logic
- `../Verification scripts/aat_validate.py`: dry-run validator

In simple terms:
- Participants see clothing pictures.
- They must respond quickly with either an **approach** action or an **avoid** action.
- The task records speed and accuracy.

## What This Task Measures

The task compares responses in two types of blocks:
- **Congruent block**: approach second-hand clothing, avoid first-hand clothing.
- **Incongruent block**: approach first-hand clothing, avoid second-hand clothing.

By comparing reaction times and errors between these blocks, you can estimate an approach-avoidance bias.

## Folder Structure You Need

The images must be in these folders:
- `SHC_Implicit/material/shc_aat_material/background_shc` (files like `shc1.png` to `shc25.png`)
- `SHC_Implicit/material/shc_aat_material/background_fhc` (files like `fhc1.png` to `fhc25.png`)

The script also supports the old legacy path:
- `SHC_Implicit/material/shc_aat_material/...`

## Before You Run

1. Make sure PsychoPy is installed and working.
2. Make sure `openpyxl` is also installed if you want automatic logbook writing.
3. Make sure both image folders above exist and contain the image sets.
4. Open Terminal in this project folder.

## How To Run

Run:

```bash
python3 "AAT Task Script/aat_practice.py"
python3 "AAT Task Script/aat_main.py"
```

To validate the non-UI AAT schedule without launching PsychoPy:

```bash
python3 "../Verification scripts/aat_validate.py"
```

Then:
1. A small dialog asks for the participant phone last-4, optional alias, and researcher.
2. Enter IDs and press OK.
3. Read the on-screen instructions.
4. `AAT Task Script/aat_practice.py` runs practice only.
5. `AAT Task Script/aat_main.py` runs the main task only and asks for the session number (`1`, `2`, or `3`).
6. Press `SPACE` to start and continue between parts.

Task-order group and smell-order group are resolved automatically from the shared logbook balance state. To look them up before a session starts:

```bash
python3 "../Verification scripts/participant_assignment.py" 0123
```

## Participant Controls

Participants can respond with keyboard or joystick:
- Joystick movement (primary): move backward = approach, move forward = avoid
- Keyboard backup keys: `Q` = approach, `M` = avoid
- `ESC` quits the task

## What Participants See (Trial Flow)

Each trial:
1. Fixation cross (`+`) for 0.5 seconds
2. One clothing image appears
3. Response:
   - If the first response is incorrect, an `X` appears over the picture
   - The picture stays visible and the trial does not advance
   - The participant must make the correct response to continue
4. Short approach/avoid animation after a response

This correction rule is used in both practice and test blocks.

## Practice Blocks and Feedback

Practice is now a separate script and keeps the current short-block structure.

- Practice block 1:
  - approach SHC, avoid FHC
- Practice block 2:
  - approach FHC, avoid SHC

Correction rule in practice and test blocks:
- If an incorrect action is made, a **red X** appears.
- The clothing picture stays visible underneath the X.
- The trial continues immediately after the participant makes the correct action.

## Counterbalancing (Detailed Explanation)

Counterbalancing means participants do the **same two block types**, but in different order.
This controls for order effects (for example, getting faster in the second block just because of practice).

### What each block means

- **Congruent block**
  - Approach: **SHC** (second-hand clothing)
  - Avoid: **FHC** (first-hand clothing)
- **Incongruent block**
  - Approach: **FHC** (first-hand clothing)
  - Avoid: **SHC** (second-hand clothing)

So the required response mapping is reversed between the two blocks.

### How order is assigned

Order depends on the numeric participant ID entered at the start:
- **Even participant number** (e.g., 2, 4, 12): Congruent first, then Incongruent
- **Odd participant number** (e.g., 1, 3, 11): Incongruent first, then Congruent
The input must be exactly the last `4` digits of the participant's phone number.

### Why this is useful

Across the full task, every participant sees both mappings:
- In one block, SHC is approached and FHC is avoided.
- In the other block, FHC is approached and SHC is avoided.

This means each stimulus category is both approached and avoided once across the experiment, which helps isolate the congruency effect from simple motor habits.

## Practice, Main, and Smell Sessions

- `aat_practice.py`
  - always runs as `session 0`
  - always uses `control_no_smell`
  - saves its own raw and cleaned output
- `aat_main.py`
  - runs as `session 1`, `2`, or `3`
  - maps the session to the smell condition through the selected smell-order group
  - uses the same counterbalance assignment as the legacy task

The smell-condition groups are:
- `control_clean_then_isovaleric`
- `control_isovaleric_then_clean`

Task order across the full experiment is tracked separately as:
- `IAT_block_first`
- `AAT_block_first`

## Current Trial Counts

- Test blocks:
  - 2 test blocks total
  - 50 trials per test block
  - **100 test trials total** (these are the trials logged in the main CSV)
- Practice blocks:
  - 2 practice blocks total in `aat_practice.py`
  - 8 scheduled practice trials per practice block (4 SHC + 4 FHC)
  - **16 scheduled practice trials total**

Combined across `aat_practice.py` and `aat_main.py`, the task flow is:
- **116 scheduled trials** (100 test + 16 practice)

Important:
- Incorrect responses trigger correction with a red X until the correct response is made in both practice and test blocks.
- Because of this, the number of response attempts can be higher than the number of scheduled trials.

## Output Files

After a run, files are saved in `data/`:
- `aat_practice_pid<last4>_s0_control_no_smell_<timestamp>.csv`
- `aat_practice_pid<last4>_s0_control_no_smell_<timestamp>_cleaned.csv`
- `aat_main_pid<last4>_s<session>_<condition>_<timestamp>.csv`
- `aat_main_pid<last4>_s<session>_<condition>_<timestamp>_cleaned.csv`

The raw PsychoPy export and the cleaned analysis file are both kept.

Each completed, interrupted, or invalid run also writes metadata to the shared workbook:
- `mrp_local/logbook/MRP_Logbook.xlsx`

## Most Important CSV Columns (Quick Meaning)

- `participant`, `session`: IDs entered at start
- `participant_code`: formatted as `pid####`
- `task`, `script_type`: whether this row came from `AAT practice` or `AAT main`
- `condition`, `smell_order_group`, `task_order_group`: experiment metadata
- `task_start_time_iso`: when the task started
- `trial_end_time_iso`: when the current trial row was recorded
- `time_elapsed_ms`: milliseconds elapsed since task start
- `block_name`: Congruent or Incongruent
- `image_name`: which picture was shown
- `category`: `SHC` (second-hand) or `FHC` (first-hand)
- `required_action`: what participant should do on that trial
- `response_action`: the participant's first response on that trial
- `correct`: `1` if the first response was correct, `0` if correction was needed
- `rt_ms`: main analysis RT in milliseconds
- `rt`: main analysis RT in seconds, measured from picture onset to the correct response that ended the trial
- `incorrect_attempts`: number of incorrect responses before the correct one
- `task_duration_ms`: total task duration in milliseconds
- `task_duration_s`: total task duration in seconds

## Full CSV Codebook

- `participant`: participant ID entered in dialog
- `participant_code`: participant code formatted as `pid####`
- `session`: session ID entered in dialog
- `task`: `AAT`
- `script_type`: `practice` or `main`
- `condition`: `control_no_smell`, `clean_odour`, or `isovaleric_acid`
- `smell_order_group`: smell-order assignment
- `task_order_group`: whether `IAT` or `AAT` came first across the experiment
- `counterbalance`: `A` (even participant) or `B` (odd participant)
- `task_start_time_iso`: ISO timestamp when the task started
- `trial_end_time_iso`: ISO timestamp when the row was recorded
- `time_elapsed_ms`: milliseconds elapsed since task start
- `block_number`: `1` or `2` in run order
- `block_name`: `Congruent` or `Incongruent`
- `trial_in_block`: trial number within current block
- `trial_global`: trial number across whole task (`1..100`)
- `image_name`: stimulus filename (for example `shc7.png`)
- `category`: `SHC` or `FHC`
- `stimulus_number`: number extracted from filename (`1..25`)
- `clothing_type`: `shirt`, `pants`, `jacket`, `hoodie`, `beanie`
- `required_action`: expected response (`approach` or `avoid`)
- `response_key`: raw input token for the first response (`q`, `m`, `joy_axis_down`, `joy_axis_up`)
- `response_source`: input source for the first response (`keyboard_button` or `joystick`)
- `response_action`: mapped first response (`approach` or `avoid`)
- `correct`: `1` = first response matched required action, `0` = first response was incorrect
- `rt_ms`: correct-response reaction time in milliseconds
- `rt`: correct-response reaction time in seconds, measured from picture onset to the response that ended the trial
- `final_response_key`: raw input token for the correct response that ended the trial
- `final_response_source`: input source for the correct response that ended the trial
- `final_response_action`: mapped correct response that ended the trial
- `incorrect_attempts`: number of incorrect responses before the correct one
- `correction_required`: `1` if at least one incorrect response occurred, `0` otherwise
- `task_duration_ms`: total duration of the task in milliseconds, repeated on each row for convenience
- `task_duration_s`: total duration of the task in seconds, repeated on each trial row for convenience

The second-based timing fields are currently retained as legacy compatibility fields during the transition to milliseconds.

## Recommended Basic Checks After Running

1. Confirm a new CSV file appears in `data/`.
2. For `aat_main.py`, open the cleaned CSV and check there are `100` rows (excluding header).
3. Confirm both `Congruent` and `Incongruent` appear in `block_name`.
4. Confirm `rt` has values on most trials.
5. Confirm the shared logbook workbook has a new `Runs` entry for the task.

## Troubleshooting

- Error says image folder not found:
  - Check that `SHC_Implicit/material/shc_aat_material/background_shc` and `background_fhc` exist.
- Script does not start because PsychoPy is missing:
  - Run from a Python environment where PsychoPy is installed, or use PsychoPy's Python.
- Logbook write fails:
  - Install `openpyxl` in the same Python environment that runs the task.
- Task closes immediately:
  - Check if `ESC` was pressed, or if the start dialog was canceled.
