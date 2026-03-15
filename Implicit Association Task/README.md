# SC-IAT for SHC (disease/disgust vs danger/fear) with Counterbalancing

This project contains a PsychoPy Single-Category IAT (SC-IAT) script:

- [iat_psychopy.py](/Users/geertmuller/Library/Mobile%20Documents/com~apple~CloudDocs/Behavioural%20Science%20RU/Compulsory/MRP_TASKS/MRP_IAT/iat_psychopy.py)

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
  - Blocks 2-3 first mapping: left = `SHC + disease/disgust`, right = `danger/fear`
  - Blocks 4-5 reversed mapping: left = `SHC + danger/fear`, right = `disease/disgust`
- `Version 2`
  - Blocks 2-3 first mapping: left = `danger/fear`, right = `SHC + disease/disgust`
  - Blocks 4-5 reversed mapping: left = `disease/disgust`, right = `SHC + danger/fear`
- `Version 3`
  - Blocks 2-3 first mapping: left = `SHC + danger/fear`, right = `disease/disgust`
  - Blocks 4-5 reversed mapping: left = `SHC + disease/disgust`, right = `danger/fear`
- `Version 4`
  - Blocks 2-3 first mapping: left = `disease/disgust`, right = `SHC + danger/fear`
  - Blocks 4-5 reversed mapping: left = `danger/fear`, right = `SHC + disease/disgust`

## Automatic version assignment

At startup, the script asks for `Participant ID` (numeric) and uses automatic assignment:

- participant IDs `1, 5, 9, ...` -> version `1`
- participant IDs `2, 6, 10, ...` -> version `2`
- participant IDs `3, 7, 11, ...` -> version `3`
- participant IDs `4, 8, 12, ...` -> version `4`

This is implemented as a repeating 1-4 cycle.

## Block structure

The script always runs 5 blocks:

1. `Practice 1` (24 trials): disease/disgust vs danger/fear
2. `Combined practice` (24 trials)
3. `Combined test` (72 trials)
4. `Reversed combined practice` (24 trials)
5. `Reversed combined test` (72 trials)

Total scheduled trials per participant: `216`
- Practice trials: `72`
- Test trials: `144` total across Blocks 3 and 5

Per-block observation counts in the current implementation:
- Block 1: `24`
- Block 2: `24`
- Block 3: `72`
- Block 4: `24`
- Block 5: `72`

The exact left/right mapping in Blocks 2–5 is automatically generated from `iat_version`.
Block 1 (attribute practice) is also aligned to the first combined mapping side setup.

## Stimulus folders

The script loads from:

- `SHC_Implicit/material/background_shc/` (SHC images)
- `SHC_Implicit/material/DIRTI_database/DIRTI Database/` (disease/disgust images)
- `SHC_Implicit/material/danger/` (danger/fear images)

Pattern split in current script:
- disease/disgust: `*injuries_infections*.jpg`, `*hygiene*.jpg`, `*body products*.jpg`
- danger/fear: all supported image files in `material/danger/`

You can change these at the top of the script.

## Participant setup

At startup, a dialog asks for:
- Participant ID
- (task version is assigned automatically from this ID)

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

Trial-level CSV file goes to:
- `data/sciat_<participant>_v<iat_version>_<timestamp>.csv`

End screen behavior:
- Shows that the task is complete and data has been saved.
- Does not display the output file path.
- Instructs the participant to ask the researcher for further instructions.

CSV columns:
- `participant_id`
- `iat_version`
- `version_source`
- `order_condition`
- `side_condition`
- `timestamp`
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
- `first_rt_sec`: latency of the first keypress from stimulus onset
- `rt_sec`: time from stimulus onset until the correct response is made
- `final_rt_sec`: same correct-response latency stored explicitly as the ending response RT
- `correct`: `1` if the first response was correct, `0` if the participant first made an error and then corrected it
- `incorrect_attempts`: number of incorrect responses before the correct response
- `correction_required`: `1` if at least one incorrect response occurred, `0` otherwise

## Running

From this folder:

```bash
python iat_psychopy.py
```

Requires PsychoPy in your active Python environment.

The task opens in full-screen mode.
