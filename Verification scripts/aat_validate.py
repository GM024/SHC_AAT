from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
CACHE_DIR = PROJECT_ROOT / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
os.environ["PYTHONPYCACHEPREFIX"] = str(CACHE_DIR)
sys.pycache_prefix = str(CACHE_DIR)
AAT_DIR = PROJECT_ROOT / "Approach Avoidance Task" / "AAT Task Script"
if str(AAT_DIR) not in sys.path:
    sys.path.insert(0, str(AAT_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import aat_core
from shared.experiment_meta import (
    CONDITION_CLEAN_ODOUR,
    CONDITION_CONTROL_NO_SMELL,
    CONDITION_ISOVALERIC_ACID,
    SCRIPT_TYPE_MAIN,
    SCRIPT_TYPE_PRACTICE,
    SMELL_ORDER_CLEAN_THEN_ISO,
    SMELL_ORDER_ISO_THEN_CLEAN,
    TASK_ORDER_AAT_BLOCK_FIRST,
    TASK_ORDER_IAT_BLOCK_FIRST,
    assign_aat_counterbalance,
    build_output_filename,
    smell_condition_order,
)


PARTICIPANT_ID_SAMPLES = ["0001", "0002", "0003", "0004", "0123"]
TASK_ORDER_SAMPLES = [TASK_ORDER_IAT_BLOCK_FIRST, TASK_ORDER_AAT_BLOCK_FIRST]
SMELL_ORDER_SAMPLES = {
    SMELL_ORDER_CLEAN_THEN_ISO: (
        CONDITION_CONTROL_NO_SMELL,
        CONDITION_CLEAN_ODOUR,
        CONDITION_ISOVALERIC_ACID,
    ),
    SMELL_ORDER_ISO_THEN_CLEAN: (
        CONDITION_CONTROL_NO_SMELL,
        CONDITION_ISOVALERIC_ACID,
        CONDITION_CLEAN_ODOUR,
    ),
}


class ValidationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def format_counts(counts: Counter | dict[str, int]) -> str:
    return ", ".join(f"{key}={value}" for key, value in sorted(counts.items()))


def summarize_trial_pairs(trials: list[dict[str, str]]) -> Counter:
    return Counter((trial["category"], trial["image_name"]) for trial in trials)


def validate_stimulus_discovery() -> list[str]:
    stimuli = aat_core.discover_stimuli(aat_core.SHC_IMAGE_DIR, aat_core.FHC_IMAGE_DIR)
    counts = Counter(trial["category"] for trial in stimuli)
    require(
        counts == Counter({"SHC": aat_core.EXPECTED_STIMULI_PER_CATEGORY, "FHC": aat_core.EXPECTED_STIMULI_PER_CATEGORY}),
        f"Stimulus discovery mismatch: expected SHC=25, FHC=25, got {format_counts(counts)}.",
    )

    pair_counts = summarize_trial_pairs(stimuli)
    repeated_pairs = sorted(f"{category}:{image_name}" for (category, image_name), count in pair_counts.items() if count > 1)
    require(
        not repeated_pairs,
        f"Stimulus discovery returned duplicate category/image pairs: {', '.join(repeated_pairs)}.",
    )
    return [
        "Stimulus discovery:",
        f"  total={len(stimuli)} | {format_counts(counts)}",
    ]


def validate_counterbalance_assignment() -> list[str]:
    lines = ["Participant parity counterbalancing:"]
    for raw_id in PARTICIPANT_ID_SAMPLES:
        participant = aat_core.parse_participant_last4(raw_id)
        counterbalance = assign_aat_counterbalance(participant.numeric_id)
        lines.append(f"  {participant.raw_last4} -> {counterbalance}")

    repeating_cycle = [assign_aat_counterbalance(value) for value in range(1, 7)]
    require(
        repeating_cycle == ["B", "A", "B", "A", "B", "A"],
        f"AAT counterbalance cycle mismatch: {repeating_cycle}",
    )
    return lines


def validate_block_order() -> list[str]:
    lines = ["Block order:"]
    expected = {
        "A": ["Congruent", "Incongruent"],
        "B": ["Incongruent", "Congruent"],
    }
    for counterbalance_condition, expected_names in expected.items():
        blocks = aat_core.get_block_mapping(counterbalance_condition)
        block_names = [block["name"] for block in blocks]
        require(
            block_names == expected_names,
            f"Counterbalance {counterbalance_condition} block order mismatch: expected {expected_names}, got {block_names}.",
        )
        lines.append(f"  {counterbalance_condition}: {', '.join(block_names)}")
    return lines


def validate_practice_trials() -> list[str]:
    stimuli = aat_core.discover_stimuli(aat_core.SHC_IMAGE_DIR, aat_core.FHC_IMAGE_DIR)
    practice_trials = aat_core.build_practice_trials(stimuli, aat_core.PRACTICE_TRIALS_PER_CATEGORY)
    counts = Counter(trial["category"] for trial in practice_trials)
    require(
        len(practice_trials) == 2 * aat_core.PRACTICE_TRIALS_PER_CATEGORY,
        f"Practice trial count mismatch: expected {2 * aat_core.PRACTICE_TRIALS_PER_CATEGORY}, got {len(practice_trials)}.",
    )
    require(
        counts == Counter({"SHC": aat_core.PRACTICE_TRIALS_PER_CATEGORY, "FHC": aat_core.PRACTICE_TRIALS_PER_CATEGORY}),
        f"Practice category counts mismatch: expected SHC=4, FHC=4, got {format_counts(counts)}.",
    )

    pair_counts = summarize_trial_pairs(practice_trials)
    repeated_pairs = sorted(f"{category}:{image_name}" for (category, image_name), count in pair_counts.items() if count > 1)
    require(
        not repeated_pairs,
        f"Practice trials repeat category/image pairs: {', '.join(repeated_pairs)}.",
    )
    return [
        "Practice trials:",
        f"  total={len(practice_trials)} | {format_counts(counts)}",
    ]


def validate_output_schema() -> list[str]:
    required_clean_fields = {
        "participant_code",
        "task_start_time_iso",
        "trial_end_time_iso",
        "time_elapsed_ms",
        "rt_ms",
        "task_duration_ms",
        "task_duration_s",
    }
    missing_fields = sorted(required_clean_fields.difference(aat_core.CLEAN_DATA_COLUMNS))
    require(
        not missing_fields,
        f"AAT cleaned output schema is missing required fields: {', '.join(missing_fields)}.",
    )
    require(
        aat_core.milliseconds_from_seconds(0.456) == 456,
        "AAT millisecond conversion helper returned an unexpected value.",
    )
    return [
        "Output schema:",
        "  participant_code, task_start_time_iso, trial_end_time_iso, time_elapsed_ms, ms RT fields, and task_duration_ms present",
    ]


def validate_main_trial_plan() -> list[str]:
    stimuli = aat_core.discover_stimuli(aat_core.SHC_IMAGE_DIR, aat_core.FHC_IMAGE_DIR)
    blocks = aat_core.get_block_mapping("A")
    total_trials = len(stimuli) * aat_core.TRIAL_REPS_PER_BLOCK * len(blocks)
    require(
        total_trials == 100,
        f"Main trial count mismatch: expected 100 total trials, got {total_trials}.",
    )

    per_block_trials = stimuli * aat_core.TRIAL_REPS_PER_BLOCK
    counts = Counter(trial["category"] for trial in per_block_trials)
    require(
        counts == Counter({"SHC": 25, "FHC": 25}),
        f"Per-block category counts mismatch: expected SHC=25, FHC=25, got {format_counts(counts)}.",
    )

    pair_counts = summarize_trial_pairs(per_block_trials)
    repeated_pairs = sorted(f"{category}:{image_name}" for (category, image_name), count in pair_counts.items() if count > 1)
    require(
        not repeated_pairs,
        f"Main block repeats category/image pairs within block: {', '.join(repeated_pairs)}.",
    )
    return [
        "Main trial plan:",
        f"  per_block={len(per_block_trials)} | total={total_trials} | {format_counts(counts)}",
    ]


def validate_smell_metadata() -> list[str]:
    lines = ["Smell-condition metadata:"]

    for smell_order_group, expected_order in SMELL_ORDER_SAMPLES.items():
        actual_order = smell_condition_order(smell_order_group)
        require(
            actual_order == expected_order,
            f"Smell-order group '{smell_order_group}' resolves to {actual_order}, expected {expected_order}.",
        )
        require(
            actual_order[0] == CONDITION_CONTROL_NO_SMELL,
            f"Smell-order group '{smell_order_group}' must start with control_no_smell.",
        )

        session_labels: list[str] = []
        for session_number, condition in enumerate(actual_order, start=1):
            for task_order_group in TASK_ORDER_SAMPLES:
                setup = aat_core.build_run_setup(
                    participant_last4="0123",
                    script_type=SCRIPT_TYPE_MAIN,
                    session_number=session_number,
                    smell_order_group=smell_order_group,
                    task_order_group=task_order_group,
                    participant_alias="P0123",
                    researcher="GM",
                )
                require(
                    setup.run.condition == condition,
                    f"Session {session_number} should map to {condition}, got {setup.run.condition}.",
                )
                filename = build_output_filename(
                    setup.run,
                    timestamp=datetime(2026, 3, 22, 12, 0, 0),
                )
                require(
                    f"_s{session_number}_{condition}_" in filename,
                    f"Output filename missing session/condition metadata: {filename}",
                )
                require(
                    f"_{aat_core.format_participant_code('0123')}_" in filename,
                    f"Output filename missing pid-style participant code: {filename}",
                )
            session_labels.append(f"s{session_number}={condition}")

        practice_setup = aat_core.build_run_setup(
            participant_last4="0123",
            script_type=SCRIPT_TYPE_PRACTICE,
            session_number=None,
            smell_order_group=smell_order_group,
            task_order_group=TASK_ORDER_IAT_BLOCK_FIRST,
            participant_alias="P0123",
            researcher="GM",
        )
        require(
            practice_setup.run.session_number == aat_core.PRACTICE_SESSION_NUMBER,
            f"Practice session number mismatch: expected {aat_core.PRACTICE_SESSION_NUMBER}, got {practice_setup.run.session_number}.",
        )
        require(
            practice_setup.run.condition == CONDITION_CONTROL_NO_SMELL,
            f"Practice condition mismatch: expected control_no_smell, got {practice_setup.run.condition}.",
        )
        practice_filename = build_output_filename(
            practice_setup.run,
            timestamp=datetime(2026, 3, 22, 12, 0, 0),
        )
        require(
            f"_s{aat_core.PRACTICE_SESSION_NUMBER}_{CONDITION_CONTROL_NO_SMELL}_" in practice_filename,
            f"Practice output filename missing expected session/condition metadata: {practice_filename}",
        )
        require(
            f"_{aat_core.format_participant_code('0123')}_" in practice_filename,
            f"Practice output filename missing pid-style participant code: {practice_filename}",
        )
        lines.append(f"  {smell_order_group}: {', '.join(session_labels)}")

    return lines


def run_validation() -> list[str]:
    lines = ["AAT dry-run validation"]
    lines.extend(validate_stimulus_discovery())
    lines.extend(validate_output_schema())
    lines.extend(validate_counterbalance_assignment())
    lines.extend(validate_block_order())
    lines.extend(validate_practice_trials())
    lines.extend(validate_main_trial_plan())
    lines.extend(validate_smell_metadata())
    lines.append("Validation passed.")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Dry-run validator for the split AAT practice/main configuration."
    )
    parser.parse_args()

    try:
        print("\n".join(run_validation()))
    except ValidationError as exc:
        print(f"VALIDATION FAILED: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
