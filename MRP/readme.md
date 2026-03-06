# PsychoPy AAT

## Run

```bash
python3 aat_psychopy.py
```

## Requirements

- PsychoPy installed in the Python environment (`pip install psychopy` or PsychoPy app Python)
- Stimulus files in:
  - `vaast images and script/shc_aat_material/background_shc` (`shc1.png` ... `shc25.png`)
  - `vaast images and script/shc_aat_material/background_fhc` (`fhc1.png` ... `fhc25.png`)

## Task setup (settings)

- Task type: keyboard Approach-Avoidance Task (AAT)
- Response controls:
  - Keyboard arrows: `DOWN` = approach, `UP` = avoid
  - Keyboard buttons: `Z` = approach, `M` = avoid
  - Joystick axis (Y): pull down = approach, push up = avoid
  - Joystick buttons: `0` = approach, `1` = avoid
- Quit key: `ESC`
- Number of blocks: `2`
- Block types:
  - `Congruent`: approach SHC, avoid FHC
  - `Incongruent`: approach FHC, avoid SHC
- Repetitions per image per block: `1`
- Total trials:
  - `50` trials per block (25 SHC + 25 FHC)
  - `100` trials total
- Timing:
  - Fixation: `0.5 s`
  - Response deadline (`MAX_RT`): `3.5 s`
  - ITI: `0.6 - 1.0 s` (deterministic jitter)
  - Response animation: `0.25 s`
- Display defaults:
  - Window size: `1280 x 800`
  - Background: black
  - Not fullscreen by default (`fullscr=False`)
- Feedback to participant:
  - No error/too-slow feedback is shown
  - Accuracy and RT are still recorded in output data

## Stimulus coding

- Category from filename prefix:
  - `shc*` -> `SHC` (Second-hand clothing)
  - `fhc*` -> `FHC` (First-hand clothing)
- Clothing type from image number:
  - `1-5`: shirt
  - `6-10`: pants
  - `11-15`: jacket
  - `16-20`: hoodie
  - `21-25`: beanie

## Counterbalancing

Counterbalancing is based on the numeric part of `participant` entered in the start dialog.

- If participant number is even -> condition `A`
  - Block 1: `Congruent`
  - Block 2: `Incongruent`
- If participant number is odd -> condition `B`
  - Block 1: `Incongruent`
  - Block 2: `Congruent`

This guarantees each stimulus is:
- approached once (in one block)
- avoided once (in the other block)

If no digits are present in the participant field, it defaults to participant `1` behavior (odd -> condition `B`).

## Block instruction messages

The task now uses full-sentence block instructions with the following wording:

- `Congruent` block message:
  - "In this block, your instructions are to approach Second-hand clothing (SHC) stimuli by moving the joystick forward, pressing the DOWN key, pressing the Z key, or pressing joystick button 0."
  - "In this block, your instructions are to avoid First-hand clothing (FHC) stimuli by moving the joystick backward, pressing the UP key, pressing the M key, or pressing joystick button 1."
- `Incongruent` block message:
  - "In this block, your instructions are to approach First-hand clothing (FHC) stimuli by moving the joystick forward, pressing the DOWN key, pressing the Z key, or pressing joystick button 0."
  - "In this block, your instructions are to avoid Second-hand clothing (SHC) stimuli by moving the joystick backward, pressing the UP key, pressing the M key, or pressing joystick button 1."

## Output files

Saved in `data/`:
- `*_AAT_PsychoPy_*.csv` -> trial-level wide text data (main analysis file)
- `*_AAT_PsychoPy_*.psydat` -> PsychoPy binary pickle

## Output codebook (CSV columns)

- `participant`: participant ID entered in dialog
- `session`: session ID entered in dialog
- `counterbalance`: `A` (even participant) or `B` (odd participant)
- `block_number`: `1` or `2` in run order
- `block_name`: `Congruent` or `Incongruent`
- `trial_in_block`: trial index within current block
- `trial_global`: trial index across whole task (`1..100`)
- `image_name`: stimulus filename (for example `shc7.png`)
- `image_path`: full path to stimulus file used
- `category`: `SHC` or `FHC`
- `stimulus_number`: numeric index extracted from filename (`1..25`)
- `clothing_type`: `shirt`, `pants`, `jacket`, `hoodie`, `beanie`
- `required_action`: expected response on this trial (`approach` or `avoid`)
- `response_key`: raw response token (`down`, `up`, `z`, `m`, `joy_axis_down`, `joy_axis_up`, `joy_button_0`, `joy_button_1`, or empty if no response)
- `response_source`: `keyboard_arrow`, `keyboard_button`, `joystick`, or empty if no response
- `response_action`: mapped action from key (`approach`, `avoid`, or empty if no response)
- `correct`: `1` = response matched required action, `0` = incorrect or no response
- `rt`: reaction time in seconds from stimulus onset to keypress (empty if no response)

## Interpreting key variables

- Congruency effect is typically computed by comparing RT and/or error rates between:
  - `Congruent` block
  - `Incongruent` block
- Use correct trials (`correct == 1`) for primary RT analyses.
- Treat missing `response_key` / `rt` as non-response (timeout at 3.5 s window).
