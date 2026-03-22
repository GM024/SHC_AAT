# SC-IAT for SHC (disease/disgust vs danger/fear) with Counterbalancing

This folder now contains a split SC-IAT workflow:

- `IAT Task Script/iat_practice.py`: dedicated practice run
- `IAT Task Script/iat_main.py`: dedicated main run
- `IAT Task Script/iat_core.py`: shared task logic
- `../Verification scripts/iat_validate.py`: dry-run validator

The task measures associations between:
- `SHC` (second-hand clothing)
- `disease/disgust`
- `danger/fear`

Participant-facing instructions explicitly define the abbreviation: `SHC = second-hand clothing`.

## What is counterbalanced

Set `iat_version` per participant (1 to 4). The script uses it to control:
1. Which combined mapping comes first
2. Whether the combined category is on the left or right

Version definitions:
- `1`: SHC + disease/disgust first, combined category left
- `2`: SHC + disease/disgust first, combined category right
- `3`: SHC + danger/fear first, combined category left
- `4`: SHC + danger/fear first, combined category right

`E` is always the left key and `I` is always the right key.

Practical meaning by version:
- `Version 1`
  - `Combined practice` and `Combined test`: left = `SHC + disease/disgust`, right = `danger/fear`
  - `Reversed combined practice` and `Reversed combined test`: left = `SHC + danger/fear`, right = `disease/disgust`
- `Version 2`
  - `Combined practice` and `Combined test`: left = `danger/fear`, right = `SHC + disease/disgust`
  - `Reversed combined practice` and `Reversed combined test`: left = `disease/disgust`, right = `SHC + danger/fear`
- `Version 3`
  - `Combined practice` and `Combined test`: left = `SHC + danger/fear`, right = `disease/disgust`
  - `Reversed combined practice` and `Reversed combined test`: left = `SHC + disease/disgust`, right = `danger/fear`
- `Version 4`
  - `Combined practice` and `Combined test`: left = `disease/disgust`, right = `SHC + danger/fear`
  - `Reversed combined practice` and `Reversed combined test`: left = `danger/fear`, right = `SHC + disease/disgust`

## Automatic version assignment

At startup, the scripts ask for the last `4` digits of the participant's phone number and use the numeric value for automatic assignment:

- participant IDs `1, 5, 9, ...` -> version `1`
- participant IDs `2, 6, 10, ...` -> version `2`
- participant IDs `3, 7, 11, ...` -> version `3`
- participant IDs `4, 8, 12, ...` -> version `4`

This is implemented as a repeating 1-4 cycle.

## Practice and Main Structure

`IAT Task Script/iat_practice.py` runs `3` practice blocks:

1. `Practice 1` (`10` trials)
2. `Combined practice` (`10` trials)
3. `Reversed combined practice` (`10` trials)

Practice uses a fixed stimulus subset, mirrors the participant's assigned IAT version, and is labeled prominently as `PRACTICE`.

`IAT Task Script/iat_main.py` runs only the two recorded test blocks:

1. `Combined test` (`72` trials)
2. `Reversed combined test` (`72` trials)

Main-block composition is fixed to `21/21/30`:

- the separate category appears `30` times
- the two combined-side categories appear `21` times each

Within a single `72`-trial main block, individual `SHC`, `Disease`, and `Danger` images are not repeated.

## Session and Condition Model

- Practice is always `session 0` and always `control_no_smell`
- Main runs use `session 1`, `session 2`, or `session 3`
- Smell conditions always begin with `control_no_smell`
- The remaining order is counterbalanced:
  - `control_clean_then_isovaleric`
  - `control_isovaleric_then_clean`

At setup, the script also asks for:

- optional participant alias
- researcher initials or name

If alias is left blank, it defaults to `P<last4>`.

Task-order group and smell-order group are resolved automatically from the shared logbook balance state. To look them up before a session starts:

```bash
python3 "../Verification scripts/participant_assignment.py" 0123
```

## Stimulus folders

The script loads from:

- `SHC_Implicit/material/background_shc/` (SHC images)
- `SHC_Implicit/material/disgust/` (disease/disgust images)
- `SHC_Implicit/material/danger/accepted/` (danger/fear images)

Pattern split in current script:
- disease/disgust: `*injuries_infections*.jpg`, `*hygiene*.jpg`, `*body products*.jpg`
- danger/fear: all supported image files in `material/danger/accepted/`

Legacy `DIRTI_database/DIRTI Database` locations are still accepted as fallback paths, but `material/disgust/` is now the primary expected folder.

## Participant setup

At startup, the split scripts ask for:
- participant phone last-4
- participant alias (optional)
- researcher
- session number for `iat_main.py`

During the task:
- Active left/right category labels remain visible at the top of the screen.
- Images are scaled to fit the display area without stretching; the original aspect ratio is preserved.
- Instruction screens show the response keys `'E'`, `'I'`, and `SPACE` in red.
- The first instruction screen shows `Instructions` in bold as the title, with centered multi-line text spaced to avoid overlap.
- Before each block, the instruction screen shows the block name in bold, followed by the mapping and response prompts in the format:
  - `Press 'E' for LEFT: ...`
  - `Press 'I' for RIGHT: ...`
- If a response is incorrect, a large red `X` appears over the stimulus and stays on screen until the correct key is pressed.
- On incorrect trials, RT is measured from stimulus onset until the participant finally presses the correct key.

## What gets saved

Trial-level CSV files go to `data/`.

Filename pattern:
- `iat_practice_pid<last4>_s0_control_no_smell_<timestamp>_v<iat_version>.csv`
- `iat_main_pid<last4>_s<session>_<condition>_<timestamp>_v<iat_version>.csv`

Each completed, interrupted, or invalid run also writes run metadata to the shared workbook:
- `mrp_local/logbook/MRP_Logbook.xlsx`

End screen behavior:
- Shows that the task is complete and data has been saved.
- Does not display the output file path.
- Instructs the participant to ask the researcher for further instructions.

CSV columns:
- `participant_id`
- `participant_code`: formatted as `pid####`
- `participant_numeric_id`
- `task`
- `script_type`
- `session_number`
- `condition`
- `smell_order_group`
- `task_order_group`
- `iat_version`
- `version_source`
- `order_condition`
- `side_condition`
- `task_start_time_iso`: ISO timestamp when the task started
- `timestamp`: legacy per-trial timestamp kept for compatibility
- `trial_end_time_iso`: ISO timestamp for when the trial row was written
- `time_elapsed_ms`: milliseconds elapsed since task start
- `block_number`
- `block_name`
- `block_type`
- `mapping_name`
- `trial_number_global`
- `trial_number_in_block`
- `stimulus_filename`
- `stimulus_category`
- `correct_response`
- `participant_response`: first key the participant pressed on that trial
- `final_response`: correct key that ended the trial
- `rt_ms`: correct-response latency in milliseconds
- `rt_sec`: time from stimulus onset until the correct response is made
- `correct`: `1` if the first response was correct, `0` if the participant first made an error and then corrected it
- `incorrect_attempts`: number of incorrect responses before the correct response
- `correction_required`: `1` if at least one incorrect response occurred, `0` otherwise

The second-based RT columns are currently retained as legacy compatibility fields during the transition to milliseconds.

## Running

From this folder:

```bash
python3 "IAT Task Script/iat_practice.py"
python3 "IAT Task Script/iat_main.py"
```

To validate the non-UI IAT schedule without launching PsychoPy:

```bash
python3 "../Verification scripts/iat_validate.py"
```

Requires `PsychoPy` in the active environment. Automatic workbook writing also requires `openpyxl`.

The task opens in full-screen mode.
