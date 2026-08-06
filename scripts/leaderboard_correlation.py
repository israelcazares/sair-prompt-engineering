#!/usr/bin/env python3
"""Reproducible cross-board correlation analysis for the SAIR EQT1 leaderboard.

Uses only the Python standard library. Raw leaderboard exports are parsed by
their stable team IDs and aligned on the exact cross-board ID intersection.
"""

from __future__ import annotations

import argparse
import hashlib
import math
import random
import re
import statistics
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Callable, Iterable, Sequence


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "leaderboard"
SCORED_PATH = DATA_DIR / "SAIR-EQT1-Leaderboard-Evaluation-Scored.txt"
RESEARCH_PATH = DATA_DIR / "SAIR-EQT1-Leaderboard-Order-5-research.txt"
DETAILS_PATH = DATA_DIR / "SAIR-EQT1-Leaderboard-Evaluation-Scored-Details.txt"
OUTPUT_PATH = DATA_DIR / "correlation_analysis.md"

TEAM_ID_RE = re.compile(r"EQT01-T\d+")
DEFAULT_SEED = 42
DEFAULT_RESAMPLES = 10_000
SENSITIVITY_CUTS = (0.33, 0.25, 0.10)


@dataclass(frozen=True)
class BoardRow:
    rank: int
    team: str
    team_id: str
    score: int
    accuracy: float
    f1: float
    parse_rate: float
    avg_cost: float
    cheatsheet_size: str


@dataclass(frozen=True)
class CorrelationSummary:
    pearson: float
    spearman: float
    pearson_bootstrap: tuple[float, float]
    spearman_bootstrap: tuple[float, float]
    pearson_fisher: tuple[float, float]
    spearman_fisher_approx: tuple[float, float]
    degenerate_bootstrap: int


@dataclass(frozen=True)
class SimulationSummary:
    low: float
    median: float
    high: float
    observed_percentile: float
    verdict: str
    valid: int
    degenerate: int


@dataclass(frozen=True)
class SubsetResult:
    selector: str
    fraction: float
    target_n: int
    cutoff: float
    n: int
    correlation: CorrelationSummary
    sd_ratio: float
    thorndike_expected_r: float
    thorndike_difference: float
    pair_selection_bootstrap: SimulationSummary
    homogeneous_null: SimulationSummary


def parse_percent(value: str) -> float:
    if not value.endswith("%"):
        raise ValueError(f"Expected percentage, got {value!r}")
    return float(value[:-1])


def parse_board(path: Path) -> list[BoardRow]:
    lines = path.read_text(encoding="utf-8").splitlines()
    rows: list[BoardRow] = []
    for index, raw_line in enumerate(lines):
        team_id = raw_line.strip()
        if not TEAM_ID_RE.fullmatch(team_id):
            continue
        try:
            row = BoardRow(
                rank=int(lines[index - 2].strip()),
                team=lines[index - 1].strip(),
                team_id=team_id,
                score=int(lines[index + 1].strip().replace(",", "")),
                accuracy=parse_percent(lines[index + 2].strip()),
                f1=parse_percent(lines[index + 3].strip()),
                parse_rate=parse_percent(lines[index + 4].strip()),
                avg_cost=float(lines[index + 5].strip().replace("$", "")),
                cheatsheet_size=lines[index + 6].strip(),
            )
        except (IndexError, ValueError) as exc:
            raise ValueError(
                f"Could not parse record around line {index + 1} of {path}"
            ) from exc
        rows.append(row)
    if not rows:
        raise ValueError(f"No leaderboard rows found in {path}")
    return rows


def index_unique(rows: Sequence[BoardRow], path: Path) -> dict[str, BoardRow]:
    indexed: dict[str, BoardRow] = {}
    duplicates: dict[str, list[BoardRow]] = {}
    for row in rows:
        if row.team_id in indexed:
            duplicates.setdefault(row.team_id, [indexed[row.team_id]]).append(row)
        else:
            indexed[row.team_id] = row
    if duplicates:
        details = "\n".join(
            f"{team_id}: {records}" for team_id, records in sorted(duplicates.items())
        )
        raise ValueError(f"Duplicate team IDs in {path}:\n{details}")
    return indexed


def mean(values: Sequence[float]) -> float:
    return sum(values) / len(values)


def sample_sd(values: Sequence[float]) -> float:
    return statistics.stdev(values)


def pearson(x: Sequence[float], y: Sequence[float]) -> float | None:
    if len(x) != len(y) or len(x) < 2:
        return None
    x_mean = mean(x)
    y_mean = mean(y)
    x_centered = [value - x_mean for value in x]
    y_centered = [value - y_mean for value in y]
    x_ss = sum(value * value for value in x_centered)
    y_ss = sum(value * value for value in y_centered)
    if x_ss == 0.0 or y_ss == 0.0:
        return None
    return sum(a * b for a, b in zip(x_centered, y_centered)) / math.sqrt(x_ss * y_ss)


def average_ranks(values: Sequence[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda index: values[index])
    ranks = [0.0] * len(values)
    start = 0
    while start < len(order):
        end = start + 1
        while end < len(order) and values[order[end]] == values[order[start]]:
            end += 1
        average_rank = ((start + 1) + end) / 2.0
        for position in range(start, end):
            ranks[order[position]] = average_rank
        start = end
    return ranks


def spearman(x: Sequence[float], y: Sequence[float]) -> float | None:
    if len(x) != len(y) or len(x) < 2:
        return None
    return pearson(average_ranks(x), average_ranks(y))


def percentile(values: Sequence[float], probability: float) -> float:
    if not values:
        raise ValueError("Cannot calculate a percentile of an empty sequence")
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def percentile_interval(values: Sequence[float]) -> tuple[float, float]:
    return percentile(values, 0.025), percentile(values, 0.975)


def fisher_interval(correlation: float, n: int) -> tuple[float, float]:
    if n <= 3:
        return math.nan, math.nan
    bounded = max(min(correlation, 1.0 - 1e-15), -1.0 + 1e-15)
    z_value = math.atanh(bounded)
    half_width = 1.959963984540054 / math.sqrt(n - 3)
    return math.tanh(z_value - half_width), math.tanh(z_value + half_width)


def named_rng(seed: int, label: str) -> random.Random:
    digest = hashlib.sha256(f"{seed}:{label}".encode("utf-8")).digest()
    derived_seed = int.from_bytes(digest[:8], byteorder="big", signed=False)
    return random.Random(derived_seed)


def bootstrap_correlations(
    pairs: Sequence[tuple[float, float]],
    resamples: int,
    rng: random.Random,
) -> tuple[list[float], list[float], int]:
    n = len(pairs)
    pearson_values: list[float] = []
    spearman_values: list[float] = []
    degenerate = 0
    for _ in range(resamples):
        sample = [pairs[rng.randrange(n)] for _ in range(n)]
        x = [pair[0] for pair in sample]
        y = [pair[1] for pair in sample]
        r_value = pearson(x, y)
        rho_value = spearman(x, y)
        if r_value is None or rho_value is None:
            degenerate += 1
            continue
        pearson_values.append(r_value)
        spearman_values.append(rho_value)
    return pearson_values, spearman_values, degenerate


def summarize_correlations(
    pairs: Sequence[tuple[float, float]],
    resamples: int,
    rng: random.Random,
) -> CorrelationSummary:
    x = [pair[0] for pair in pairs]
    y = [pair[1] for pair in pairs]
    r_value = pearson(x, y)
    rho_value = spearman(x, y)
    if r_value is None or rho_value is None:
        raise ValueError("Observed sample has undefined correlation")
    r_bootstrap, rho_bootstrap, degenerate = bootstrap_correlations(
        pairs, resamples, rng
    )
    return CorrelationSummary(
        pearson=r_value,
        spearman=rho_value,
        pearson_bootstrap=percentile_interval(r_bootstrap),
        spearman_bootstrap=percentile_interval(rho_bootstrap),
        pearson_fisher=fisher_interval(r_value, len(pairs)),
        spearman_fisher_approx=fisher_interval(rho_value, len(pairs)),
        degenerate_bootstrap=degenerate,
    )


def top_subset(
    pairs: Sequence[tuple[float, float]],
    selector_index: int,
    fraction: float,
) -> tuple[list[tuple[float, float]], int, float]:
    target_n = math.ceil(len(pairs) * fraction)
    selector_values = sorted(
        (pair[selector_index] for pair in pairs), reverse=True
    )
    cutoff = selector_values[target_n - 1]
    subset = [pair for pair in pairs if pair[selector_index] >= cutoff]
    return subset, target_n, cutoff


def thorndike_expected_restricted_r(unrestricted_r: float, sd_ratio: float) -> float:
    denominator = math.sqrt(
        1.0 - unrestricted_r * unrestricted_r * (1.0 - sd_ratio * sd_ratio)
    )
    return unrestricted_r * sd_ratio / denominator


def simulation_summary(
    values: Sequence[float],
    observed: float,
    degenerate: int,
    requested: int,
) -> SimulationSummary:
    low = percentile(values, 0.025)
    median = percentile(values, 0.5)
    high = percentile(values, 0.975)
    observed_percentile = (
        100.0 * sum(value <= observed for value in values) / len(values)
    )
    verdict = "inside" if low <= observed <= high else "outside"
    return SimulationSummary(
        low=low,
        median=median,
        high=high,
        observed_percentile=observed_percentile,
        verdict=verdict,
        valid=requested - degenerate,
        degenerate=degenerate,
    )


def simulate_pair_selection(
    full_pairs: Sequence[tuple[float, float]],
    selector_index: int,
    fraction: float,
    observed: float,
    resamples: int,
    rng: random.Random,
) -> SimulationSummary:
    n = len(full_pairs)
    values: list[float] = []
    degenerate = 0
    for _ in range(resamples):
        sample = [full_pairs[rng.randrange(n)] for _ in range(n)]
        subset, _, _ = top_subset(sample, selector_index, fraction)
        r_value = pearson(
            [pair[0] for pair in subset], [pair[1] for pair in subset]
        )
        if r_value is None:
            degenerate += 1
            continue
        values.append(r_value)
    if not values:
        raise ValueError("All empirical selection bootstrap replicates degenerated")
    return simulation_summary(values, observed, degenerate, resamples)


def fit_linear_model(
    selector: Sequence[float], outcome: Sequence[float]
) -> tuple[float, float, list[float]]:
    selector_mean = mean(selector)
    outcome_mean = mean(outcome)
    selector_ss = sum((value - selector_mean) ** 2 for value in selector)
    if selector_ss == 0.0:
        raise ValueError("Cannot fit model with zero selector variance")
    slope = sum(
        (x_value - selector_mean) * (y_value - outcome_mean)
        for x_value, y_value in zip(selector, outcome)
    ) / selector_ss
    intercept = outcome_mean - slope * selector_mean
    residuals = [
        y_value - (intercept + slope * x_value)
        for x_value, y_value in zip(selector, outcome)
    ]
    residual_mean = mean(residuals)
    centered_residuals = [value - residual_mean for value in residuals]
    return intercept, slope, centered_residuals


def simulate_homogeneous_null(
    full_pairs: Sequence[tuple[float, float]],
    selector_index: int,
    fraction: float,
    observed: float,
    resamples: int,
    rng: random.Random,
) -> SimulationSummary:
    selector = [pair[selector_index] for pair in full_pairs]
    outcome_index = 1 - selector_index
    outcome = [pair[outcome_index] for pair in full_pairs]
    intercept, slope, residuals = fit_linear_model(selector, outcome)
    n = len(full_pairs)
    values: list[float] = []
    degenerate = 0

    for _ in range(resamples):
        simulated_pairs: list[tuple[float, float]] = []
        for _ in range(n):
            selector_value = selector[rng.randrange(n)]
            residual = residuals[rng.randrange(n)]
            outcome_value = intercept + slope * selector_value + residual
            if selector_index == 0:
                simulated_pairs.append((selector_value, outcome_value))
            else:
                simulated_pairs.append((outcome_value, selector_value))
        subset, _, _ = top_subset(simulated_pairs, selector_index, fraction)
        r_value = pearson(
            [pair[0] for pair in subset], [pair[1] for pair in subset]
        )
        if r_value is None:
            degenerate += 1
            continue
        values.append(r_value)

    if not values:
        raise ValueError("All homogeneous-null bootstrap replicates degenerated")
    return simulation_summary(values, observed, degenerate, resamples)


def format_number(value: float, digits: int = 4) -> str:
    if math.isnan(value):
        return "NA"
    return f"{value:.{digits}f}"


def format_interval(interval: tuple[float, float]) -> str:
    return f"[{format_number(interval[0])}, {format_number(interval[1])}]"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def markdown_report(
    scored_rows: Sequence[BoardRow],
    research_rows: Sequence[BoardRow],
    intersection_ids: Sequence[str],
    full_summary: CorrelationSummary,
    subset_results: Sequence[SubsetResult],
    seed: int,
    resamples: int,
) -> str:
    lines: list[str] = [
        "# Cross-Board Correlation Analysis",
        "",
        f"- Analysis date: {date.today().isoformat()}",
        f"- Git HEAD: `{git_head()}`",
        f"- Root seed: `{seed}`",
        f"- Resamples per bootstrap/simulation: `{resamples:,}`",
        "- Top-subset rule: `ceil(fraction × n)` observations define the cutoff;",
        "  all observations tied at the cutoff are included.",
        "",
        "## Source Integrity",
        "",
        f"- Scored export SHA-256: `{file_sha256(SCORED_PATH)}`",
        f"- Research export SHA-256: `{file_sha256(RESEARCH_PATH)}`",
        f"- Scored-details export SHA-256: `{file_sha256(DETAILS_PATH)}`",
        "",
        "## Unit-of-Analysis Validation",
        "",
        f"- Scored rows: `{len(scored_rows)}`",
        f"- Scored unique team IDs: `{len({row.team_id for row in scored_rows})}`",
        "- Scored duplicate team IDs: `0`",
        f"- Research rows: `{len(research_rows)}`",
        f"- Research unique team IDs: `{len({row.team_id for row in research_rows})}`",
        "- Research duplicate team IDs: `0`",
        f"- Cross-board ID intersection: `{len(intersection_ids)}`",
        "- Scored-only IDs: `0`",
        "- Research-only IDs: `0`",
        "",
        "The exported boards therefore contain 310 rows corresponding to 310",
        "unique team IDs on each board, with an exact 310-ID intersection.",
        "",
        "## Full Sample",
        "",
        "| Metric | Estimate | Bootstrap 95% CI | Fisher 95% CI |",
        "|---|---:|---:|---:|",
        (
            f"| Pearson r | {format_number(full_summary.pearson)} | "
            f"{format_interval(full_summary.pearson_bootstrap)} | "
            f"{format_interval(full_summary.pearson_fisher)} |"
        ),
        (
            f"| Spearman rho | {format_number(full_summary.spearman)} | "
            f"{format_interval(full_summary.spearman_bootstrap)} | "
            f"{format_interval(full_summary.spearman_fisher_approx)} |"
        ),
        "",
        (
            "Degenerate full-sample correlation bootstrap replicates: "
            f"`{full_summary.degenerate_bootstrap}`."
        ),
        "The Fisher interval for Spearman rho is included only as an",
        "approximation for comparison; the bootstrap interval is primary.",
        "",
        "## Conditioned Subsets and Range Restriction",
        "",
        "| Selector | Cut | Target n | Cutoff | Actual n | Pearson r | Pearson bootstrap 95% CI | Spearman rho | Spearman bootstrap 95% CI | SD ratio u | Thorndike expected r | Observed - expected |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for result in subset_results:
        summary = result.correlation
        lines.append(
            f"| {result.selector} | {result.fraction:.0%} | {result.target_n} | "
            f"{result.cutoff:.1f}% | {result.n} | "
            f"{format_number(summary.pearson)} | "
            f"{format_interval(summary.pearson_bootstrap)} | "
            f"{format_number(summary.spearman)} | "
            f"{format_interval(summary.spearman_bootstrap)} | "
            f"{format_number(result.sd_ratio)} | "
            f"{format_number(result.thorndike_expected_r)} | "
            f"{format_number(result.thorndike_difference)} |"
        )

    lines.extend(
        [
            "",
            "Thorndike Case II is reported as an analytic reference under direct",
            "range restriction and a homogeneous linear relationship. It is not",
            "used as a standalone hypothesis test.",
            "",
            "## Empirical Pair-Selection Bootstrap",
            "",
            "This bootstrap follows the requested pair-resampling algorithm. It",
            "preserves heterogeneity present in the observed pairs and therefore",
            "is not a homogeneous null simulation.",
            "",
            "| Selector | Cut | Observed r | Bootstrap p2.5 | Median | Bootstrap p97.5 | Observed percentile | Interval verdict | Valid | Degenerate |",
            "|---|---:|---:|---:|---:|---:|---:|---|---:|---:|",
        ]
    )
    for result in subset_results:
        simulation = result.pair_selection_bootstrap
        lines.append(
            f"| {result.selector} | {result.fraction:.0%} | "
            f"{format_number(result.correlation.pearson)} | "
            f"{format_number(simulation.low)} | "
            f"{format_number(simulation.median)} | "
            f"{format_number(simulation.high)} | "
            f"{simulation.observed_percentile:.2f}% | "
            f"{simulation.verdict} | {simulation.valid} | "
            f"{simulation.degenerate} |"
        )

    lines.extend(
        [
            "",
            "## Homogeneous Linear Null Bootstrap",
            "",
            "For each selector, an ordinary least-squares model is fit on the full",
            "sample with the other board as outcome. Each replicate independently",
            "resamples selector values and centered residuals, reconstructs 310",
            "pairs under one homogeneous linear relationship, and reapplies the",
            "same cutoff and tie rule. This is the simulation used for the",
            "inside/outside homogeneity verdict.",
            "",
            "| Selector | Cut | Observed r | Null p2.5 | Null median | Null p97.5 | Observed percentile | Homogeneity verdict | Valid | Degenerate |",
            "|---|---:|---:|---:|---:|---:|---:|---|---:|---:|",
        ]
    )
    for result in subset_results:
        simulation = result.homogeneous_null
        lines.append(
            f"| {result.selector} | {result.fraction:.0%} | "
            f"{format_number(result.correlation.pearson)} | "
            f"{format_number(simulation.low)} | "
            f"{format_number(simulation.median)} | "
            f"{format_number(simulation.high)} | "
            f"{simulation.observed_percentile:.2f}% | "
            f"{simulation.verdict} expected interval | "
            f"{simulation.valid} | {simulation.degenerate} |"
        )

    lines.extend(
        [
            "",
            "## Fisher Intervals for Conditioned Subsets",
            "",
            "| Selector | Cut | n | Pearson Fisher 95% CI | Spearman Fisher approximation 95% CI | Degenerate correlation bootstrap replicates |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for result in subset_results:
        summary = result.correlation
        lines.append(
            f"| {result.selector} | {result.fraction:.0%} | {result.n} | "
            f"{format_interval(summary.pearson_fisher)} | "
            f"{format_interval(summary.spearman_fisher_approx)} | "
            f"{summary.degenerate_bootstrap} |"
        )

    lines.extend(
        [
            "",
            "## Parameters",
            "",
            "- Pair alignment key: exact `EQT01-Txxxxx` team ID.",
            "- Correlations use leaderboard `Avg Accuracy` percentages.",
            "- Bootstrap confidence intervals use percentile endpoints.",
            "- Pair bootstrap resamples paired scored/research observations.",
            "- Named pseudorandom streams are deterministically derived from the",
            f"  root seed `{seed}` using SHA-256.",
            "- Sensitivity cuts: top 33%, top 25%, and top 10% by each board.",
            "- Ties use average ranks for Spearman rho.",
            "",
        ]
    )
    return "\n".join(lines)


def analyze(seed: int, resamples: int) -> str:
    for path in (SCORED_PATH, RESEARCH_PATH, DETAILS_PATH):
        if not path.exists():
            raise FileNotFoundError(f"Required source file is missing: {path}")

    scored_rows = parse_board(SCORED_PATH)
    research_rows = parse_board(RESEARCH_PATH)
    scored_by_id = index_unique(scored_rows, SCORED_PATH)
    research_by_id = index_unique(research_rows, RESEARCH_PATH)

    scored_ids = set(scored_by_id)
    research_ids = set(research_by_id)
    intersection_ids = sorted(scored_ids & research_ids)
    if len(scored_rows) != 310 or len(research_rows) != 310:
        raise ValueError(
            f"Expected 310 rows per board, got {len(scored_rows)} scored and "
            f"{len(research_rows)} research"
        )
    if len(intersection_ids) != 310 or scored_ids != research_ids:
        raise ValueError(
            "Expected an exact 310-ID intersection; "
            f"intersection={len(intersection_ids)}, "
            f"scored_only={len(scored_ids - research_ids)}, "
            f"research_only={len(research_ids - scored_ids)}"
        )

    full_pairs = [
        (
            scored_by_id[team_id].accuracy,
            research_by_id[team_id].accuracy,
        )
        for team_id in intersection_ids
    ]
    full_summary = summarize_correlations(
        full_pairs,
        resamples,
        named_rng(seed, "full-correlation-bootstrap"),
    )
    full_r = full_summary.pearson

    subset_results: list[SubsetResult] = []
    for fraction in SENSITIVITY_CUTS:
        for selector, selector_index in (("scored", 0), ("research", 1)):
            label = f"{selector}-{fraction:.2f}"
            subset, target_n, cutoff = top_subset(
                full_pairs, selector_index, fraction
            )
            correlation = summarize_correlations(
                subset,
                resamples,
                named_rng(seed, f"{label}-conditional-correlation-bootstrap"),
            )
            full_selector = [pair[selector_index] for pair in full_pairs]
            subset_selector = [pair[selector_index] for pair in subset]
            sd_ratio = sample_sd(subset_selector) / sample_sd(full_selector)
            expected = thorndike_expected_restricted_r(full_r, sd_ratio)
            pair_selection = simulate_pair_selection(
                full_pairs,
                selector_index,
                fraction,
                correlation.pearson,
                resamples,
                named_rng(seed, f"{label}-pair-selection-bootstrap"),
            )
            homogeneous_null = simulate_homogeneous_null(
                full_pairs,
                selector_index,
                fraction,
                correlation.pearson,
                resamples,
                named_rng(seed, f"{label}-homogeneous-null"),
            )
            subset_results.append(
                SubsetResult(
                    selector=selector,
                    fraction=fraction,
                    target_n=target_n,
                    cutoff=cutoff,
                    n=len(subset),
                    correlation=correlation,
                    sd_ratio=sd_ratio,
                    thorndike_expected_r=expected,
                    thorndike_difference=correlation.pearson - expected,
                    pair_selection_bootstrap=pair_selection,
                    homogeneous_null=homogeneous_null,
                )
            )

    report = markdown_report(
        scored_rows=scored_rows,
        research_rows=research_rows,
        intersection_ids=intersection_ids,
        full_summary=full_summary,
        subset_results=subset_results,
        seed=seed,
        resamples=resamples,
    )
    OUTPUT_PATH.write_text(report, encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--resamples", type=int, default=DEFAULT_RESAMPLES)
    args = parser.parse_args()
    if args.resamples < 1:
        parser.error("--resamples must be positive")
    report = analyze(seed=args.seed, resamples=args.resamples)
    print(report)


if __name__ == "__main__":
    main()
