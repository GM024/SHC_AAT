from __future__ import annotations

import argparse
import os
import random
import sys
from collections import Counter
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
CACHE_DIR = PROJECT_ROOT / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
os.environ["PYTHONPYCACHEPREFIX"] = str(CACHE_DIR)
sys.pycache_prefix = str(CACHE_DIR)
IAT_DIR = PROJECT_ROOT / "Implicit Association Task" / "IAT Task Script"
if str(IAT_DIR) not in sys.path:
    sys.path.insert(0, str(IAT_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import iat_core
from shared.experiment_meta import (
    CONDITION_CONTROL_NO_SMELL,
    CONDITION_CLEAN_ODOUR,
    CONDITION_ISOVALERIC_ACID,
    RunIdentity,
    SCRIPT_TYPE_MAIN,
    SCRIPT_TYPE_PRACTICE,
    SMELL_ORDER_CLEAN_THEN_ISO,
    SMELL_ORDER_ISO_THEN_CLEAN,
    TASK_IAT,
    TASK_ORDER_AAT_BLOCK_FIRST,
    TASK_ORDER_IAT_BLOCK_FIRST,
    assign_iat_version,
    build_output_filename,
    parse_participant_last4,
    smell_condition_order,
)


EXPECTED_PRACTICE_BLOCK_NAMES = [
    "Practice 1",
    "Combined practice",
    "Reversed combined practice",
]
EXPECTED_MAIN_BLOCK_NAMES = [
    "Combined test",
    "Reversed combined test",
]

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
PARTICIPANT_ID_SAMPLES = ["0001", "0002", "0003", "0004", "0005", "0123"]
TASK_ORDER_SAMPLES = [TASK_ORDER_IAT_BLOCK_FIRST, TASK_ORDER_AAT_BLOCK_FIRST]


class ValidationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def format_counts(counts: Counter | dict[str, int]) -> str:
    return ", ".join(f"{category}={count}" for category, count in sorted(counts.items()))


def summarize_exposures(trials: list[dict[str, str]]) -> dict[str, Counter]:
    exposure_counts: dict[str, Counter] = {}
    for category in {trial["stimulus_category"] for trial in trials}:
        exposure_counts[category] = Counter(
            trial["stimulus_file"] for trial in trials if trial["stimulus_category"] == category
        )
    return exposure_counts


def validate_block_headers(
    blocks: list[dict[str, object]],
    *,
    expected_names: list[str],
    expected_trials: int,
    label: str,
) -> list[str]:
    require(
        len(blocks) == len(expected_names),
        f"{label} must contain {len(expected_names)} blocks, found {len(blocks)}.",
    )
    lines: list[str] = []
    for index, block in enumerate(blocks):
        require(
            str(block["block_name"]) == expected_names[index],
            f"{label} block {index + 1} must be '{expected_names[index]}', got '{block['block_name']}'.",
        )
        require(
            int(block["n_trials"]) == expected_trials,
            f"{label} block '{block['block_name']}' must contain {expected_trials} trials, "
            f"got {block['n_trials']}.",
        )
        lines.append(f"{block['block_name']} ({block['n_trials']} trials)")
    return lines


def validate_trial_distribution(
    *,
    block: dict[str, object],
    trials: list[dict[str, str]],
    require_unique_within_block: bool,
) -> str:
    counts = Counter(trial["stimulus_category"] for trial in trials)
    expected_counts = Counter(dict(block["category_counts"]))
    require(
        counts == expected_counts,
        f"Block '{block['block_name']}' category counts mismatch: expected "
        f"{format_counts(expected_counts)}, got {format_counts(counts)}.",
    )

    exposure_counts = summarize_exposures(trials)
    if require_unique_within_block:
        for category, file_counts in exposure_counts.items():
            repeated_files = sorted(
                Path(file_path).name for file_path, count in file_counts.items() if count > 1
            )
            require(
                not repeated_files,
                f"Block '{block['block_name']}' repeats {category} files within the block: "
                f"{', '.join(repeated_files)}.",
            )

    max_exposure_by_category = {
        category: max(file_counts.values(), default=0)
        for category, file_counts in exposure_counts.items()
    }
    return (
        f"{block['block_name']}: {format_counts(counts)} | "
        f"max per-image exposure {format_counts(max_exposure_by_category)}"
    )


def validate_version_schedule(
    version: int,
    stimulus_pools: dict[str, list[Path]],
) -> list[str]:
    rng = random.Random(version)
    version_cfg = iat_core.get_version_config(version)
    lines = [
        f"Version {version}: order={version_cfg['order_condition']}, side={version_cfg['side_condition']}"
    ]

    practice_blocks = iat_core.build_practice_blocks(version_cfg)
    main_blocks = iat_core.build_main_blocks(version_cfg)

    practice_headers = validate_block_headers(
        practice_blocks,
        expected_names=EXPECTED_PRACTICE_BLOCK_NAMES,
        expected_trials=iat_core.TRIALS_PRACTICE_BLOCK,
        label="Practice schedule",
    )
    main_headers = validate_block_headers(
        main_blocks,
        expected_names=EXPECTED_MAIN_BLOCK_NAMES,
        expected_trials=iat_core.TRIALS_MAIN_BLOCK,
        label="Main schedule",
    )
    lines.append(f"  Practice blocks: {', '.join(practice_headers)}")
    lines.append(f"  Main blocks: {', '.join(main_headers)}")

    practice_pools = iat_core.build_practice_pools(stimulus_pools)
    for block in practice_blocks:
        trials = iat_core.build_block_trials(block, practice_pools, rng)
        lines.append(
            "  Practice composition: "
            + validate_trial_distribution(
                block=block,
                trials=trials,
                require_unique_within_block=False,
            )
        )

    for block in main_blocks:
        trials = iat_core.build_block_trials(block, stimulus_pools, rng)
        lines.append(
            "  Main composition: "
            + validate_trial_distribution(
                block=block,
                trials=trials,
                require_unique_within_block=True,
            )
        )

    return lines


def validate_version_assignment() -> list[str]:
    lines = ["Participant ID version assignment:"]
    for raw_id in PARTICIPANT_ID_SAMPLES:
        participant = parse_participant_last4(raw_id)
        version = assign_iat_version(participant.numeric_id)
        lines.append(f"  {participant.raw_last4} -> version {version}")

    repeating_cycle = [assign_iat_version(value) for value in range(1, 9)]
    require(
        repeating_cycle == [1, 2, 3, 4, 1, 2, 3, 4],
        f"IAT version cycle mismatch: {repeating_cycle}",
    )
    return lines


def validate_output_schema() -> list[str]:
    fields = iat_core.fieldnames()
    required_fields = {
        "participant_code",
        "task_start_time_iso",
        "trial_end_time_iso",
        "time_elapsed_ms",
        "rt_ms",
        "rt_sec",
    }
    missing_fields = sorted(required_fields.difference(fields))
    require(
        not missing_fields,
        f"IAT output schema is missing required fields: {', '.join(missing_fields)}.",
    )
    require(
        iat_core.milliseconds_from_seconds(0.5234) == 523,
        "IAT millisecond conversion helper returned an unexpected value.",
    )
    return [
        "Output schema:",
        "  participant_code, task_start_time_iso, trial_end_time_iso, time_elapsed_ms, and ms RT fields present",
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

        participant = parse_participant_last4("0123")
        version = assign_iat_version(participant.numeric_id)
        session_labels = []
        for session_number, condition in enumerate(actual_order, start=1):
            for task_order_group in TASK_ORDER_SAMPLES:
                run = RunIdentity(
                    participant=participant,
                    task=TASK_IAT,
                    script_type=SCRIPT_TYPE_MAIN,
                    session_number=session_number,
                    condition=condition,
                    task_order_group=task_order_group,
                    smell_order_group=smell_order_group,
                )
                filename = build_output_filename(
                    run,
                    timestamp=iat_core.datetime(2026, 3, 22, 12, 0, 0),
                    iat_version=version,
                )
                require(
                    f"_s{session_number}_{condition}_" in filename,
                    f"Output filename missing session/condition metadata: {filename}",
                )
                require(
                    f"_{iat_core.format_participant_code(participant.raw_last4)}_" in filename,
                    f"Output filename missing pid-style participant code: {filename}",
                )
            session_labels.append(f"s{session_number}={condition}")

        practice_run = RunIdentity(
            participant=participant,
            task=TASK_IAT,
            script_type=SCRIPT_TYPE_PRACTICE,
            session_number=iat_core.PRACTICE_SESSION_NUMBER,
            condition=CONDITION_CONTROL_NO_SMELL,
            task_order_group=TASK_ORDER_IAT_BLOCK_FIRST,
            smell_order_group=smell_order_group,
        )
        practice_filename = build_output_filename(
            practice_run,
            timestamp=iat_core.datetime(2026, 3, 22, 12, 0, 0),
            iat_version=version,
        )
        require(
            f"_s{iat_core.PRACTICE_SESSION_NUMBER}_{CONDITION_CONTROL_NO_SMELL}_" in practice_filename,
            f"Practice output filename missing expected session/condition metadata: {practice_filename}",
        )
        require(
            f"_{iat_core.format_participant_code(participant.raw_last4)}_" in practice_filename,
            f"Practice output filename missing pid-style participant code: {practice_filename}",
        )
        lines.append(f"  {smell_order_group}: {', '.join(session_labels)}")

    return lines


def validate_stimulus_pools(stimulus_pools: dict[str, list[Path]]) -> list[str]:
    lines = ["Stimulus pools:"]
    for category, required_unique in {
        iat_core.CAT_SHC: 21,
        iat_core.CAT_DISEASE: 30,
        iat_core.CAT_DANGER: 30,
    }.items():
        available = len(stimulus_pools[category])
        require(
            available >= required_unique,
            f"{category} pool is too small for main-block uniqueness: need at least {required_unique}, "
            f"found {available}.",
        )
        lines.append(f"  {category}: {available} files available")
    return lines


def run_validation() -> list[str]:
    lines = ["IAT dry-run validation"]
    stimulus_pools = iat_core.load_stimulus_pools()
    lines.extend(validate_stimulus_pools(stimulus_pools))
    lines.extend(validate_version_assignment())
    lines.extend(validate_output_schema())
    lines.extend(validate_smell_metadata())
    for version in range(1, 5):
        lines.extend(validate_version_schedule(version, stimulus_pools))
    lines.append("Validation passed.")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Dry-run validator for the split IAT practice/main configuration."
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
