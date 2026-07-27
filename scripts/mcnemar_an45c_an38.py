#!/usr/bin/env python3
"""Paired McNemar comparison for the AN45c and AN38 n=400 runs."""

from __future__ import annotations

import argparse
import csv
import json
import math
import subprocess
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AN45C = (
    REPO_ROOT
    / "results"
    / "AN45c_rawprompt_gptoss_hard3_gpt-oss-120b_20260414_000546.json"
)
DEFAULT_AN38 = (
    REPO_ROOT
    / "results"
    / "AN38_gptoss_hard3_full_gpt-oss-120b_20260404_170146.json"
)
DEFAULT_OUTPUT_DIR = REPO_ROOT / "results" / "partitions"
CSV_FIELDS = [
    "id",
    "eq1",
    "eq2",
    "label",
    "an45c_predicted",
    "an38_predicted",
]


def load_results(path: Path) -> dict[str, dict]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)

    rows = payload.get("results")
    if not isinstance(rows, list):
        raise ValueError(f"{path}: missing results array")

    by_id: dict[str, dict] = {}
    for row in rows:
        if not isinstance(row, dict) or "id" not in row or "correct" not in row:
            raise ValueError(f"{path}: result missing id or correct")
        problem_id = row["id"]
        if problem_id in by_id:
            raise ValueError(f"{path}: duplicate problem id {problem_id}")
        by_id[problem_id] = row
    return by_id


def exact_binomial_p_value(b: int, c: int) -> float:
    discordant = b + c
    lower_tail = sum(
        math.comb(discordant, k) for k in range(min(b, c) + 1)
    ) / (2**discordant)
    return min(1.0, 2.0 * lower_tail)


def source_display(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(resolved)


def current_git_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def write_partitions(
    output_dir: Path,
    partitions: dict[str, list[dict]],
    an45c_path: Path,
    an38_path: Path,
    generated_commit: str,
    n_aligned: int,
    b: int,
    c: int,
    statistic: float,
    p_value: float,
    method: str,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, rows in partitions.items():
        path = output_dir / f"{name}.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
            writer.writeheader()
            writer.writerows(rows)

    generated_at = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )
    readme = f"""# AN45c vs AN38 Paired Partitions

Generated: {generated_at}
Generated at commit: `{generated_commit}`
Paper version: `paper-sair-v16.tex`

## Sources
- AN45c path: `{source_display(an45c_path)}`
- AN45c filename: `{an45c_path.name}`
- AN38 path: `{source_display(an38_path)}`
- AN38 filename: `{an38_path.name}`

## Partition Counts
- Aligned problems: {n_aligned}
- `an45c_only_correct.csv`: {len(partitions["an45c_only_correct"])}
- `an38_only_correct.csv`: {len(partitions["an38_only_correct"])}
- `both_correct.csv`: {len(partitions["both_correct"])}
- `both_wrong.csv`: {len(partitions["both_wrong"])}

## McNemar Test
- b (AN45c correct, AN38 incorrect): {b}
- c (AN45c incorrect, AN38 correct): {c}
- Chi-square statistic (continuity-corrected): {statistic:.10f}
- p-value: {p_value:.12g}
- Method: {method}
"""
    (output_dir / "README.md").write_text(readme, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--an45c", type=Path, default=DEFAULT_AN45C)
    parser.add_argument("--an38", type=Path, default=DEFAULT_AN38)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    an45c = load_results(args.an45c)
    an38 = load_results(args.an38)
    ids45 = set(an45c)
    ids38 = set(an38)
    if ids45 != ids38:
        only45 = sorted(ids45 - ids38)
        only38 = sorted(ids38 - ids45)
        raise ValueError(
            "problem-id sets differ: "
            f"AN45c-only={len(only45)}, AN38-only={len(only38)}"
        )

    for problem_id in ids45:
        if an45c[problem_id].get("label") != an38[problem_id].get("label"):
            raise ValueError(f"gold-label mismatch for {problem_id}")

    partitions: dict[str, list[dict]] = {
        "an45c_only_correct": [],
        "an38_only_correct": [],
        "both_correct": [],
        "both_wrong": [],
    }
    for problem_id in sorted(ids45):
        row45 = an45c[problem_id]
        row38 = an38[problem_id]
        correct45 = bool(row45["correct"])
        correct38 = bool(row38["correct"])
        if correct45 and not correct38:
            partition = "an45c_only_correct"
        elif not correct45 and correct38:
            partition = "an38_only_correct"
        elif correct45 and correct38:
            partition = "both_correct"
        else:
            partition = "both_wrong"
        partitions[partition].append(
            {
                "id": problem_id,
                "eq1": row45.get("eq1", ""),
                "eq2": row45.get("eq2", ""),
                "label": row45.get("label", ""),
                "an45c_predicted": row45.get("predicted", ""),
                "an38_predicted": row38.get("predicted", ""),
            }
        )

    both_correct = len(partitions["both_correct"])
    b = len(partitions["an45c_only_correct"])
    c = len(partitions["an38_only_correct"])
    both_incorrect = len(partitions["both_wrong"])
    discordant = b + c
    statistic = (
        (abs(b - c) - 1) ** 2 / discordant if discordant else 0.0
    )

    if discordant < 25:
        method = "exact two-sided binomial"
        p_value = exact_binomial_p_value(b, c)
    else:
        method = "chi-square(1 df), continuity-corrected"
        p_value = math.erfc(math.sqrt(statistic / 2.0))

    write_partitions(
        args.output_dir,
        partitions,
        args.an45c,
        args.an38,
        current_git_commit(),
        len(ids45),
        b,
        c,
        statistic,
        p_value,
        method,
    )

    print(f"AN45c file: {args.an45c}")
    print(f"AN38 file: {args.an38}")
    print(f"partition output directory: {args.output_dir}")
    print(f"n_aligned: {len(ids45)}")
    print("contingency table (correctness):")
    print("                      AN38 correct  AN38 incorrect")
    print(f"AN45c correct        {both_correct:13d}  {b:15d}")
    print(f"AN45c incorrect      {c:13d}  {both_incorrect:15d}")
    print(f"b (AN45c correct, AN38 incorrect): {b}")
    print(f"c (AN45c incorrect, AN38 correct): {c}")
    print(f"discordant pairs (b+c): {discordant}")
    print(f"McNemar statistic (continuity-corrected): {statistic:.10f}")
    print(f"p-value method: {method}")
    print(f"p-value: {p_value:.12g}")


if __name__ == "__main__":
    main()
