# SC-IAT for SHC (Disease vs Danger) with Counterbalancing

This project contains a PsychoPy Single-Category IAT (SC-IAT) script:

- [iat_psychopy.py](/Users/geertmuller/Library/Mobile%20Documents/com~apple~CloudDocs/Behavioural%20Science%20RU/Compulsory/MRP_TASKS/MRP_IAT/iat_psychopy.py)

The task measures associations between:
- `SHC` (Second-hand clothing)
- `Disease`
- `Danger`

Participant-facing instructions explicitly define the abbreviation: `SHC = Second-hand clothing`.

## What is counterbalanced

Set `iat_version` per participant (1 to 4). The script uses it to control:
1. Which combined mapping comes first
2. Whether the combined category is on the left or right

Version definitions:
- `1`: SHC + Disease first, combined category left
- `2`: SHC + Disease first, combined category right
- `3`: SHC + Danger first, combined category left
- `4`: SHC + Danger first, combined category right

`E` is always the left key and `I` is always the right key.

Practical meaning by version:
- `Version 1`
  - Blocks 2-3 first mapping: left = `SHC + Disease`, right = `Danger`
  - Blocks 4-5 reversed mapping: left = `SHC + Danger`, right = `Disease`
- `Version 2`
  - Blocks 2-3 first mapping: left = `Danger`, right = `SHC + Disease`
  - Blocks 4-5 reversed mapping: left = `Disease`, right = `SHC + Danger`
- `Version 3`
  - Blocks 2-3 first mapping: left = `SHC + Danger`, right = `Disease`
  - Blocks 4-5 reversed mapping: left = `SHC + Disease`, right = `Danger`
- `Version 4`
  - Blocks 2-3 first mapping: left = `Disease`, right = `SHC + Danger`
  - Blocks 4-5 reversed mapping: left = `Danger`, right = `SHC + Disease`

## Automatic version assignment

At startup, the script asks for `Participant ID` (numeric) and uses automatic assignment:

- participant IDs `1, 5, 9, ...` -> version `1`
- participant IDs `2, 6, 10, ...` -> version `2`
- participant IDs `3, 7, 11, ...` -> version `3`
- participant IDs `4, 8, 12, ...` -> version `4`

This is implemented as a repeating 1-4 cycle.

## Block structure

The script always runs 5 blocks:

1. `Practice 1` (24 trials): Disease vs Danger
2. `Combined practice` (24 trials)
3. `Combined test` (72 trials)
4. `Reversed combined practice` (24 trials)
5. `Reversed combined test` (72 trials)

The exact left/right mapping in Blocks 2–5 is automatically generated from `iat_version`.
Block 1 (attribute practice) is also aligned to the first combined mapping side setup.

## Stimulus folders

The script loads from:

- `material/background_shc/` (SHC images)
- `material/DIRTI_database/DIRTI Database/` (attribute images)

Pattern split in current script:
- Disease: `*injuries_infections*.jpg`, `*hygiene*.jpg`, `*body products*.jpg`
- Danger: `*death*.jpg`

You can change these at the top of the script.

## Participant setup

At startup, a dialog asks for:
- Participant ID
- (task version is assigned automatically from this ID)

During the task:
- Active left/right category labels remain visible at the top of the screen.
- If a response is incorrect, a red `X` appears and stays on screen until the correct key is pressed.

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
- `participant_response`
- `rt_sec`
- `correct`

## Running

From this folder:

```bash
python iat_psychopy.py
```

Requires PsychoPy in your active Python environment.
