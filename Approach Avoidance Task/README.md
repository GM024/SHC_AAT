# PsychoPy AAT Task Guide (Plain Language)

This folder contains an **Approach-Avoidance Task (AAT)** about clothing images.

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
2. Make sure this file exists: `aat_psychopy.py`.
3. Make sure both image folders above exist and contain the image sets.
4. Open Terminal in this project folder.

## How To Run

Run:

```bash
python3 aat_psychopy.py
```

Then:
1. A small dialog asks for `participant` and `session`.
2. Enter IDs and press OK.
3. Read the on-screen instructions.
4. For each block, complete a short practice first.
5. Press `SPACE` to start and continue between parts.

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

Before each real test block, participants complete a short practice block with the same mapping.

- Practice before Congruent test block:
  - approach SHC, avoid FHC
- Practice before Incongruent test block:
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

If the participant field has no digits, the script treats it like participant `1` (odd).

### Why this is useful

Across the full task, every participant sees both mappings:
- In one block, SHC is approached and FHC is avoided.
- In the other block, FHC is approached and SHC is avoided.

This means each stimulus category is both approached and avoided once across the experiment, which helps isolate the congruency effect from simple motor habits.

## Current Trial Counts (From Current Code)

- Test blocks:
  - 2 test blocks total
  - 50 trials per test block
  - **100 test trials total** (these are the trials logged in the main CSV)
- Practice blocks:
  - 2 practice blocks total (one before each test block)
  - 8 scheduled practice trials per practice block (4 SHC + 4 FHC)
  - **16 scheduled practice trials total**

Total task flow is therefore:
- **116 scheduled trials** (100 test + 16 practice)

Important:
- Incorrect responses trigger correction with a red X until the correct response is made in both practice and test blocks.
- Because of this, the number of response attempts can be higher than the number of scheduled trials.

## Output Files

After a complete run, files are saved in `data/`:
- `*_AAT_PsychoPy_*.csv` (raw PsychoPy wide-text export)
- `*_AAT_PsychoPy_*_cleaned.csv` (cleaned trial-level analysis file)

## Most Important CSV Columns (Quick Meaning)

- `participant`, `session`: IDs entered at start
- `block_name`: Congruent or Incongruent
- `image_name`: which picture was shown
- `category`: `SHC` (second-hand) or `FHC` (first-hand)
- `required_action`: what participant should do on that trial
- `response_action`: the participant's first response on that trial
- `correct`: `1` if the first response was correct, `0` if correction was needed
- `rt`: main analysis RT in seconds, measured from picture onset to the correct response that ended the trial
- `first_rt`: reaction time of the first response in seconds
- `final_rt`: reaction time of the correct response that ended the trial
- `incorrect_attempts`: number of incorrect responses before the correct one
- `task_duration_s`: total task duration in seconds

## Full CSV Codebook

- `participant`: participant ID entered in dialog
- `session`: session ID entered in dialog
- `counterbalance`: `A` (even participant) or `B` (odd participant)
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
- `rt`: correct-response reaction time in seconds, measured from picture onset to the response that ended the trial
- `first_rt`: first-response reaction time in seconds
- `final_response_key`: raw input token for the correct response that ended the trial
- `final_response_source`: input source for the correct response that ended the trial
- `final_response_action`: mapped correct response that ended the trial
- `final_rt`: same correct-response reaction time stored explicitly for clarity
- `incorrect_attempts`: number of incorrect responses before the correct one
- `correction_required`: `1` if at least one incorrect response occurred, `0` otherwise
- `task_duration_s`: total duration of the task in seconds, repeated on each trial row for convenience

## Recommended Basic Checks After Running

1. Confirm a new CSV file appears in `data/`.
2. Open the CSV and check there are 100 rows (excluding header).
3. Confirm both `Congruent` and `Incongruent` appear in `block_name`.
4. Confirm `rt` has values on most trials.

## Troubleshooting

- Error says image folder not found:
  - Check that `SHC_Implicit/material/shc_aat_material/background_shc` and `background_fhc` exist.
- Script does not start because PsychoPy is missing:
  - Run from a Python environment where PsychoPy is installed, or use PsychoPy's Python.
- Task closes immediately:
  - Check if `ESC` was pressed, or if the start dialog was canceled.
