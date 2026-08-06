#!/usr/bin/env python3
"""Validate and reconstruct the SAIR EQT1 per-problem matrix dataset.

The original extraction contains complete contiguous matrix segments but no
submission identifier. This script enumerates assignments of those segments,
applies per-cell coverage constraints, validates candidates against public
leaderboard accuracies, and writes the unique validated reconstruction.

Candidate enumeration is data-driven:

1. Every contiguous source segment is either assigned to the author's
   submission or to the winning submission.
2. Raw candidates retain assignments whose row totals match the cell coverage
   implied by the official details export and the recovered-row artifact.
3. Per-cell candidates must produce exactly one 1..200 matrix for every scored
   model/problem-set cell for both submissions.
4. Official-accuracy validation retains only assignments reproducing all 18
   published scored cell accuracies. The reconstruction fails unless exactly
   one candidate remains.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "leaderboard"

DEFAULT_ORIGINAL = DATA_DIR / "sair_matrix_extraction.csv"
DEFAULT_RECOVERED = (
    DATA_DIR / "SAIR-EQT1-EQT01-T00458-missing-normal-326.csv"
)
DEFAULT_SCORED = DATA_DIR / "SAIR-EQT1-Leaderboard-Evaluation-Scored.txt"
DEFAULT_RESEARCH = DATA_DIR / "SAIR-EQT1-Leaderboard-Order-5-research.txt"
DEFAULT_SCORED_DETAILS = (
    DATA_DIR / "SAIR-EQT1-Leaderboard-Evaluation-Scored-Details.txt"
)
DEFAULT_OUTPUT = DATA_DIR / "sair_matrix_extraction_v2.csv"

ORIGINAL_COLUMNS = [
    "board",
    "model",
    "problem_set",
    "problem_index",
    "problem_id",
    "result",
    "runs",
]
FINAL_COLUMNS = ["submission_id", *ORIGINAL_COLUMNS]
TEAM_ID_RE = re.compile(r"EQT01-T\d+")
MODELS = {
    "GPT-OSS 120B",
    "Gemma 4 31B IT",
    "Llama 3.3 70B Instruct",
}
PROBLEM_SETS = {"normal", "hard", "extra_hard", "order5"}


class ValidationError(RuntimeError):
    """Raised when an input or reconstruction invariant fails."""


@dataclass(frozen=True)
class MatrixRow:
    values: dict[str, str]
    source_path: Path
    source_line: int

    @property
    def board(self) -> str:
        return self.values["board"]

    @property
    def model(self) -> str:
        return self.values["model"]

    @property
    def problem_set(self) -> str:
        return self.values["problem_set"]

    @property
    def problem_index(self) -> int:
        return int(self.values["problem_index"])

    @property
    def group(self) -> tuple[str, str, str]:
        return self.board, self.model, self.problem_set


@dataclass(frozen=True)
class Segment:
    source_path: Path
    rows: tuple[MatrixRow, ...]

    @property
    def group(self) -> tuple[str, str, str]:
        return self.rows[0].group

    @property
    def start_line(self) -> int:
        return self.rows[0].source_line

    @property
    def end_line(self) -> int:
        return self.rows[-1].source_line


@dataclass(frozen=True)
class BoardEntry:
    rank: int
    team: str
    team_id: str
    average_accuracy: float


@dataclass(frozen=True)
class Reconstruction:
    raw_candidates: int
    per_cell_candidates: int
    validated_candidates: int
    author_id: str
    author_team: str
    winner_id: str
    winner_team: str
    final_rows: tuple[dict[str, str], ...]
    official_accuracies_pass: bool
    disagreement_gpt_pass: bool
    disagreement_gemma_pass: bool
    research_average: float


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_percent(value: str) -> float:
    if not value.endswith("%"):
        raise ValidationError(f"Expected percentage, got {value!r}")
    return float(value[:-1])


def load_csv(path: Path, expected_columns: Sequence[str]) -> list[MatrixRow]:
    if not path.exists():
        raise ValidationError(f"Missing required input: {path}")
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != list(expected_columns):
            raise ValidationError(
                f"Unexpected header in {path}: {reader.fieldnames}; "
                f"expected {list(expected_columns)}"
            )
        rows = [
            MatrixRow(dict(row), source_path=path, source_line=line_number)
            for line_number, row in enumerate(reader, start=2)
        ]
    if not rows:
        raise ValidationError(f"No data rows in {path}")
    for row in rows:
        validate_matrix_row(row, has_submission_id="submission_id" in expected_columns)
    return rows


def validate_matrix_row(row: MatrixRow, has_submission_id: bool) -> None:
    values = row.values
    if has_submission_id and not TEAM_ID_RE.fullmatch(values["submission_id"]):
        raise ValidationError(
            f"Invalid submission ID at {row.source_path}:{row.source_line}"
        )
    if values["board"] not in {"scored", "research"}:
        raise ValidationError(
            f"Invalid board at {row.source_path}:{row.source_line}"
        )
    if values["model"] not in MODELS:
        raise ValidationError(
            f"Invalid model at {row.source_path}:{row.source_line}"
        )
    if values["problem_set"] not in PROBLEM_SETS:
        raise ValidationError(
            f"Invalid problem set at {row.source_path}:{row.source_line}"
        )
    try:
        index = int(values["problem_index"])
    except ValueError as exc:
        raise ValidationError(
            f"Invalid problem index at {row.source_path}:{row.source_line}"
        ) from exc
    if not 1 <= index <= 200:
        raise ValidationError(
            f"Out-of-range problem index at {row.source_path}:{row.source_line}"
        )

    expected_prefix = {
        "normal": "N",
        "hard": "H",
        "extra_hard": "EH",
        "order5": "O5",
    }[values["problem_set"]]
    if values["problem_id"] != f"{expected_prefix}_{index:03d}":
        raise ValidationError(
            f"Problem ID/index mismatch at {row.source_path}:{row.source_line}"
        )

    runs = values["runs"]
    if len(runs) not in {1, 3} or any(character not in "GRU" for character in runs):
        raise ValidationError(
            f"Invalid runs encoding at {row.source_path}:{row.source_line}"
        )
    if len(runs) == 1:
        expected_result = {"G": "correct", "R": "incorrect", "U": "unparsed"}[runs]
    elif len(set(runs)) == 1:
        raise ValidationError(
            f"Unexpected identical three-run encoding at "
            f"{row.source_path}:{row.source_line}"
        )
    elif runs.count("U") >= 2:
        expected_result = "unparsed"
    else:
        expected_result = "mixed"
    if values["result"] != expected_result:
        raise ValidationError(
            f"Result/runs mismatch at {row.source_path}:{row.source_line}: "
            f"{values['result']!r} versus {runs!r}"
        )


def split_contiguous_segments(rows: Sequence[MatrixRow]) -> list[Segment]:
    segments: list[Segment] = []
    current: list[MatrixRow] = []
    previous: MatrixRow | None = None
    for row in rows:
        starts_new = (
            previous is None
            or row.group != previous.group
            or row.problem_index <= previous.problem_index
        )
        if starts_new and current:
            segments.append(Segment(current[0].source_path, tuple(current)))
            current = []
        current.append(row)
        previous = row
    if current:
        segments.append(Segment(current[0].source_path, tuple(current)))
    validate_source_segments(rows, segments)
    return segments


def validate_source_segments(
    source_rows: Sequence[MatrixRow], segments: Sequence[Segment]
) -> None:
    retained_lines: list[int] = []
    for segment in segments:
        lines = [row.source_line for row in segment.rows]
        if lines != list(range(segment.start_line, segment.end_line + 1)):
            raise ValidationError(
                f"Non-contiguous source segment in {segment.source_path}: "
                f"{segment.start_line}-{segment.end_line}"
            )
        indices = [row.problem_index for row in segment.rows]
        if indices != list(range(indices[0], indices[-1] + 1)):
            raise ValidationError(
                f"Non-contiguous problem indices in {segment.source_path}: "
                f"{segment.start_line}-{segment.end_line}"
            )
        retained_lines.extend(lines)
    expected_lines = [row.source_line for row in source_rows]
    if sorted(retained_lines) != sorted(expected_lines):
        raise ValidationError(
            f"Segments overlap or omit source rows in {source_rows[0].source_path}"
        )


def parse_board(path: Path) -> list[BoardEntry]:
    lines = path.read_text(encoding="utf-8").splitlines()
    entries: list[BoardEntry] = []
    for index, line in enumerate(lines):
        team_id = line.strip()
        if not TEAM_ID_RE.fullmatch(team_id):
            continue
        try:
            entries.append(
                BoardEntry(
                    rank=int(lines[index - 2].strip()),
                    team=lines[index - 1].strip(),
                    team_id=team_id,
                    average_accuracy=parse_percent(lines[index + 2].strip()),
                )
            )
        except (IndexError, ValueError) as exc:
            raise ValidationError(
                f"Could not parse leaderboard entry around {path}:{index + 1}"
            ) from exc
    if len(entries) != 310 or len({entry.team_id for entry in entries}) != 310:
        raise ValidationError(
            f"Expected 310 unique board entries in {path}, got {len(entries)}"
        )
    return entries


def find_unique_team(entries: Sequence[BoardEntry], team: str) -> BoardEntry:
    matches = [entry for entry in entries if entry.team == team]
    if len(matches) != 1:
        raise ValidationError(
            f"Expected one public board entry for {team!r}, got {len(matches)}"
        )
    return matches[0]


def parse_scored_details(
    path: Path, team_id: str
) -> dict[tuple[str, str], float]:
    lines = path.read_text(encoding="utf-8").splitlines()
    id_positions = [
        index for index, line in enumerate(lines) if TEAM_ID_RE.fullmatch(line.strip())
    ]
    matching = [position for position in id_positions if lines[position].strip() == team_id]
    if len(matching) != 1:
        raise ValidationError(
            f"Expected one details block for {team_id}, got {len(matching)}"
        )
    start = matching[0]
    later_ids = [position for position in id_positions if position > start]
    end = later_ids[0] - 2 if later_ids else len(lines)
    block = lines[start:end]

    accuracies: dict[tuple[str, str], float] = {}
    for index, line in enumerate(block):
        model = line.strip()
        if model not in MODELS:
            continue
        problem_set_position = None
        for candidate in range(index + 1, min(index + 6, len(block))):
            if block[candidate].strip() in {"normal", "hard", "extra_hard"}:
                problem_set_position = candidate
                break
        if problem_set_position is None:
            continue
        problem_set = block[problem_set_position].strip()
        accuracy_value = None
        for candidate in range(problem_set_position + 1, min(problem_set_position + 5, len(block))):
            value = block[candidate].strip()
            if re.fullmatch(r"\d+(?:\.\d+)?%", value):
                accuracy_value = parse_percent(value)
                break
        if accuracy_value is None:
            raise ValidationError(
                f"Could not parse {model}/{problem_set} accuracy for {team_id}"
            )
        key = (model, problem_set)
        if key in accuracies:
            raise ValidationError(f"Duplicate details metric for {team_id}: {key}")
        accuracies[key] = accuracy_value

    if len(accuracies) != 9:
        raise ValidationError(
            f"Expected 9 scored cell accuracies for {team_id}, got "
            f"{len(accuracies)}: {accuracies}"
        )
    return accuracies


def expanded_runs(row: MatrixRow | dict[str, str]) -> str:
    runs = row.values["runs"] if isinstance(row, MatrixRow) else row["runs"]
    return runs * 3 if len(runs) == 1 else runs


def reconstructed_accuracy(rows: Sequence[MatrixRow | dict[str, str]]) -> float:
    if not rows:
        raise ValidationError("Cannot reconstruct accuracy from zero rows")
    correct = sum(expanded_runs(row).count("G") for row in rows)
    return round(100.0 * correct / (3 * len(rows)), 1)


def disagreement_rate(rows: Sequence[dict[str, str]]) -> float:
    if not rows:
        raise ValidationError("Cannot calculate disagreement from zero rows")
    mixed = sum(row["result"] == "mixed" for row in rows)
    return round(100.0 * mixed / len(rows), 1)


def group_rows(
    rows: Iterable[MatrixRow],
) -> dict[tuple[str, str, str], list[MatrixRow]]:
    grouped: dict[tuple[str, str, str], list[MatrixRow]] = defaultdict(list)
    for row in rows:
        grouped[row.group].append(row)
    return grouped


def exact_cell_coverage(rows: Sequence[MatrixRow]) -> bool:
    indices = [row.problem_index for row in rows]
    return len(indices) == 200 and sorted(indices) == list(range(1, 201))


def enumerate_raw_candidates(
    scored_segments: Sequence[Segment], author_original_rows: int
) -> list[tuple[int, ...]]:
    """Enumerate all segment assignments satisfying raw row-count constraints.

    The search space is the power set of scored source segments. A selected
    segment is assigned to the author's submission; every unselected scored
    segment is assigned to the winner. No candidate-count constants are used.
    """

    candidates: list[tuple[int, ...]] = []
    for size in range(len(scored_segments) + 1):
        for selected in itertools.combinations(range(len(scored_segments)), size):
            selected_rows = sum(len(scored_segments[index].rows) for index in selected)
            if selected_rows == author_original_rows:
                candidates.append(selected)
    return candidates


def satisfies_per_cell_constraints(
    selected: set[int],
    scored_segments: Sequence[Segment],
    recovered_rows: Sequence[MatrixRow],
    expected_cells: set[tuple[str, str]],
) -> bool:
    author_rows = [
        row
        for index, segment in enumerate(scored_segments)
        if index in selected
        for row in segment.rows
    ]
    winner_rows = [
        row
        for index, segment in enumerate(scored_segments)
        if index not in selected
        for row in segment.rows
    ]
    author_grouped = group_rows([*author_rows, *recovered_rows])
    winner_grouped = group_rows(winner_rows)
    author_cells = {
        (model, problem_set)
        for board, model, problem_set in author_grouped
        if board == "scored"
    }
    winner_cells = {
        (model, problem_set)
        for board, model, problem_set in winner_grouped
        if board == "scored"
    }
    if author_cells != expected_cells or winner_cells != expected_cells:
        return False
    for model, problem_set in expected_cells:
        key = ("scored", model, problem_set)
        if not exact_cell_coverage(author_grouped[key]):
            return False
        if not exact_cell_coverage(winner_grouped[key]):
            return False
    return True


def accuracies_match(
    selected: set[int],
    scored_segments: Sequence[Segment],
    recovered_rows: Sequence[MatrixRow],
    author_official: dict[tuple[str, str], float],
    winner_official: dict[tuple[str, str], float],
) -> bool:
    author_rows = [
        row
        for index, segment in enumerate(scored_segments)
        if index in selected
        for row in segment.rows
    ]
    winner_rows = [
        row
        for index, segment in enumerate(scored_segments)
        if index not in selected
        for row in segment.rows
    ]
    author_grouped = group_rows([*author_rows, *recovered_rows])
    winner_grouped = group_rows(winner_rows)
    for cell, official in author_official.items():
        if reconstructed_accuracy(author_grouped[("scored", *cell)]) != official:
            return False
    for cell, official in winner_official.items():
        if reconstructed_accuracy(winner_grouped[("scored", *cell)]) != official:
            return False
    return True


def with_submission_id(row: MatrixRow, submission_id: str) -> dict[str, str]:
    return {
        "submission_id": submission_id,
        **{column: row.values[column] for column in ORIGINAL_COLUMNS},
    }


def deterministic_sort_key(row: dict[str, str]) -> tuple[str, str, str, str, int]:
    return (
        row["submission_id"],
        row["board"],
        row["model"],
        row["problem_set"],
        int(row["problem_index"]),
    )


def validate_final_group_contiguity(rows: Sequence[dict[str, str]]) -> None:
    seen_groups: set[tuple[str, str, str, str]] = set()
    previous_group: tuple[str, str, str, str] | None = None
    group_indices: list[int] = []

    def finish_group(
        group: tuple[str, str, str, str] | None, indices: list[int]
    ) -> None:
        if group is None:
            return
        if group in seen_groups:
            raise ValidationError(f"Final group is non-contiguous: {group}")
        seen_groups.add(group)
        if sorted(indices) != list(range(1, 201)):
            raise ValidationError(
                f"Final group lacks exact 1..200 coverage: {group}"
            )

    for row in rows:
        group = (
            row["submission_id"],
            row["board"],
            row["model"],
            row["problem_set"],
        )
        if group != previous_group:
            finish_group(previous_group, group_indices)
            previous_group = group
            group_indices = []
        group_indices.append(int(row["problem_index"]))
    finish_group(previous_group, group_indices)


def validate_final_keys(rows: Sequence[dict[str, str]]) -> int:
    keys = [
        (
            row["submission_id"],
            row["board"],
            row["model"],
            row["problem_set"],
            int(row["problem_index"]),
        )
        for row in rows
    ]
    return len(keys) - len(set(keys))


def reconstruct(
    original_rows: Sequence[MatrixRow],
    recovered_rows: Sequence[MatrixRow],
    scored_entries: Sequence[BoardEntry],
    research_entries: Sequence[BoardEntry],
    scored_details_path: Path,
) -> Reconstruction:
    author_scored = find_unique_team(scored_entries, "Israel Cazares")
    author_research = find_unique_team(research_entries, "Israel Cazares")
    if author_scored.team_id != author_research.team_id:
        raise ValidationError(
            "Israel Cazares has inconsistent public IDs across boards"
        )
    winner_entries = [entry for entry in scored_entries if entry.rank == 1]
    if len(winner_entries) != 1:
        raise ValidationError("Could not identify a unique scored-board winner")
    winner = winner_entries[0]
    if winner.team_id == author_scored.team_id:
        raise ValidationError("Author and winner IDs unexpectedly coincide")

    recovered_ids = {row.values["submission_id"] for row in recovered_rows}
    if recovered_ids != {author_scored.team_id}:
        raise ValidationError(
            f"Recovered artifact ID mismatch: {recovered_ids} versus "
            f"{author_scored.team_id}"
        )

    author_official = parse_scored_details(
        scored_details_path, author_scored.team_id
    )
    winner_official = parse_scored_details(scored_details_path, winner.team_id)
    expected_cells = set(author_official)
    if expected_cells != set(winner_official):
        raise ValidationError("Author/winner scored details cover different cells")

    original_segments = split_contiguous_segments(original_rows)
    recovered_segments = split_contiguous_segments(recovered_rows)
    if len(recovered_segments) != 2:
        raise ValidationError(
            f"Expected two recovered source segments, got {len(recovered_segments)}"
        )

    scored_segments = [
        segment for segment in original_segments if segment.group[0] == "scored"
    ]
    research_segments = [
        segment for segment in original_segments if segment.group[0] == "research"
    ]
    if sum(len(segment.rows) for segment in research_segments) != 600:
        raise ValidationError("Expected exactly 600 original research rows")
    research_grouped = group_rows(
        row for segment in research_segments for row in segment.rows
    )
    if len(research_grouped) != 3 or any(
        not exact_cell_coverage(rows) for rows in research_grouped.values()
    ):
        raise ValidationError("Research rows do not form three complete cells")

    expected_author_scored_rows = len(expected_cells) * 200
    author_original_rows = expected_author_scored_rows - len(recovered_rows)
    raw_candidates = enumerate_raw_candidates(
        scored_segments, author_original_rows
    )
    per_cell_candidates = [
        candidate
        for candidate in raw_candidates
        if satisfies_per_cell_constraints(
            set(candidate), scored_segments, recovered_rows, expected_cells
        )
    ]
    validated_candidates = [
        candidate
        for candidate in per_cell_candidates
        if accuracies_match(
            set(candidate),
            scored_segments,
            recovered_rows,
            author_official,
            winner_official,
        )
    ]
    if len(validated_candidates) != 1:
        raise ValidationError(
            "Official-accuracy validation did not produce one unique candidate: "
            f"raw={len(raw_candidates)}, per_cell={len(per_cell_candidates)}, "
            f"validated={len(validated_candidates)}"
        )

    selected = set(validated_candidates[0])
    author_original = [
        row
        for index, segment in enumerate(scored_segments)
        if index in selected
        for row in segment.rows
    ]
    winner_original = [
        row
        for index, segment in enumerate(scored_segments)
        if index not in selected
        for row in segment.rows
    ]
    research_original = [
        row for segment in research_segments for row in segment.rows
    ]
    final_rows = [
        *(with_submission_id(row, author_scored.team_id) for row in author_original),
        *(
            with_submission_id(row, author_scored.team_id)
            for row in recovered_rows
        ),
        *(with_submission_id(row, author_scored.team_id) for row in research_original),
        *(with_submission_id(row, winner.team_id) for row in winner_original),
    ]
    final_rows.sort(key=deterministic_sort_key)

    duplicate_keys = validate_final_keys(final_rows)
    if len(final_rows) != 4_200 or duplicate_keys != 0:
        raise ValidationError(
            f"Final dataset shape invalid: rows={len(final_rows)}, "
            f"duplicate_keys={duplicate_keys}"
        )
    validate_final_group_contiguity(final_rows)

    final_grouped: dict[
        tuple[str, str, str, str], list[dict[str, str]]
    ] = defaultdict(list)
    for row in final_rows:
        final_grouped[
            (
                row["submission_id"],
                row["board"],
                row["model"],
                row["problem_set"],
            )
        ].append(row)

    official_pass = True
    for cell, official in author_official.items():
        rows = final_grouped[
            (author_scored.team_id, "scored", cell[0], cell[1])
        ]
        official_pass &= reconstructed_accuracy(rows) == official
    for cell, official in winner_official.items():
        rows = final_grouped[(winner.team_id, "scored", cell[0], cell[1])]
        official_pass &= reconstructed_accuracy(rows) == official

    research_rows = [
        row
        for row in final_rows
        if row["submission_id"] == author_scored.team_id
        and row["board"] == "research"
    ]
    research_average = reconstructed_accuracy(research_rows)
    official_pass &= research_average == author_research.average_accuracy

    gpt_normal = final_grouped[
        (author_scored.team_id, "scored", "GPT-OSS 120B", "normal")
    ]
    gemma_normal = final_grouped[
        (author_scored.team_id, "scored", "Gemma 4 31B IT", "normal")
    ]
    gpt_pass = disagreement_rate(gpt_normal) == 39.0
    gemma_pass = disagreement_rate(gemma_normal) == 16.0
    if not official_pass or not gpt_pass or not gemma_pass:
        raise ValidationError(
            f"Final metric validation failed: official={official_pass}, "
            f"gpt39={gpt_pass}, gemma16={gemma_pass}"
        )

    return Reconstruction(
        raw_candidates=len(raw_candidates),
        per_cell_candidates=len(per_cell_candidates),
        validated_candidates=len(validated_candidates),
        author_id=author_scored.team_id,
        author_team=author_scored.team,
        winner_id=winner.team_id,
        winner_team=winner.team,
        final_rows=tuple(final_rows),
        official_accuracies_pass=official_pass,
        disagreement_gpt_pass=gpt_pass,
        disagreement_gemma_pass=gemma_pass,
        research_average=research_average,
    )


def write_dataset(path: Path, rows: Sequence[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=FINAL_COLUMNS, lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def pass_fail(value: bool) -> str:
    return "PASS" if value else "FAIL"


def run(args: argparse.Namespace) -> tuple[Reconstruction, str]:
    original_rows = load_csv(args.original, ORIGINAL_COLUMNS)
    recovered_rows = load_csv(args.recovered, FINAL_COLUMNS)
    scored_entries = parse_board(args.scored)
    research_entries = parse_board(args.research)
    reconstruction = reconstruct(
        original_rows,
        recovered_rows,
        scored_entries,
        research_entries,
        args.scored_details,
    )
    write_dataset(args.output, reconstruction.final_rows)
    dataset_hash = sha256(args.output)
    return reconstruction, dataset_hash


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", type=Path, default=DEFAULT_ORIGINAL)
    parser.add_argument("--recovered", type=Path, default=DEFAULT_RECOVERED)
    parser.add_argument("--scored", type=Path, default=DEFAULT_SCORED)
    parser.add_argument("--research", type=Path, default=DEFAULT_RESEARCH)
    parser.add_argument(
        "--scored-details", type=Path, default=DEFAULT_SCORED_DETAILS
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        reconstruction, dataset_hash = run(args)
    except (OSError, ValidationError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    print(f"Original extraction .... {args.original.resolve()}")
    print(
        f"Author submission ...... {reconstruction.author_id} "
        f"({reconstruction.author_team})"
    )
    print(
        f"Winning submission ..... {reconstruction.winner_id} "
        f"({reconstruction.winner_team})"
    )
    print()
    print(f"Raw candidates ........ {reconstruction.raw_candidates}")
    print(f"Per-cell candidates ... {reconstruction.per_cell_candidates}")
    print(f"Unique validated ...... {reconstruction.validated_candidates}")
    print()
    print(f"Merged rows ........... {len(reconstruction.final_rows)}")
    print(
        "Duplicate keys ........ "
        f"{validate_final_keys(reconstruction.final_rows)}"
    )
    print()
    print(
        "Official accuracies ... "
        f"{pass_fail(reconstruction.official_accuracies_pass)}"
    )
    print(
        "Disagreement 39.0 ..... "
        f"{pass_fail(reconstruction.disagreement_gpt_pass)}"
    )
    print(
        "Disagreement 16.0 ..... "
        f"{pass_fail(reconstruction.disagreement_gemma_pass)}"
    )
    print()
    print(f"Dataset SHA-256 ....... {dataset_hash}")


if __name__ == "__main__":
    main()
