#!/usr/bin/env python3
"""Task-level statistical analysis for the combined 20-task DeepSeek run.

The task is the unit of analysis. Repeats are averaged within task-condition,
then conditions are compared across paired tasks. No attempt-level pooling.
"""

from __future__ import annotations

import json
import math
import random
import statistics
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import wilcoxon

ROOT = Path(__file__).resolve().parents[1]
ATTEMPTS = ROOT / "data" / "derived" / "mechanism-20-combined" / "attempts.json"
FINAL = ROOT / "data" / "mechanism-20-final" / "tasks.json"
OUT = ROOT / "results" / "mechanism-20-combined" / "statistical_analysis.json"
SEED = 20261116
N_BOOT = 10_000
N_PERM = 100_000

METRICS = [
    "resolved",
    "test_before_edit",
    "read_before_edit",
    "time_to_first_edit_seconds",
    "total_tokens",
    "verification_rate",
    "test_calls",
    "steps",
    "f2p_fraction",
    "p2p_fraction",
    "budget_exhausted",
]
CONTINUOUS = {
    "time_to_first_edit_seconds",
    "total_tokens",
    "verification_rate",
    "test_calls",
    "steps",
    "f2p_fraction",
    "p2p_fraction",
}
CONTRASTS = [("C", "B"), ("B", "A"), ("C", "A")]


def mean(values):
    values = list(values)
    return sum(values) / len(values) if values else None


def sd(values):
    values = list(values)
    return statistics.stdev(values) if len(values) > 1 else 0.0


def sign_test(wins: int, losses: int) -> float:
    n = wins + losses
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, k) for k in range(min(wins, losses) + 1)) / (2**n)
    return min(1.0, 2 * tail)


def rank_biserial(diffs):
    diffs = [diff for diff in diffs if diff != 0]
    if not diffs:
        return 0.0
    ordered = sorted(range(len(diffs)), key=lambda index: abs(diffs[index]))
    ranks = [0.0] * len(diffs)
    index = 0
    while index < len(ordered):
        end = index
        while end + 1 < len(ordered) and abs(diffs[ordered[end + 1]]) == abs(diffs[ordered[index]]):
            end += 1
        rank = (index + 1 + end + 1) / 2
        for position in range(index, end + 1):
            ranks[ordered[position]] = rank
        index = end + 1
    positive = sum(ranks[i] for i, diff in enumerate(diffs) if diff > 0)
    negative = sum(ranks[i] for i, diff in enumerate(diffs) if diff < 0)
    return (positive - negative) / (positive + negative) if positive + negative else 0.0


def bootstrap_ci(diffs, n_boot=N_BOOT, seed=SEED):
    rng = random.Random(seed)
    n = len(diffs)
    means = [sum(diffs[rng.randrange(n)] for _ in range(n)) / n for _ in range(n_boot)]
    means.sort()
    return [means[int(0.025 * n_boot)], means[min(n_boot - 1, int(0.975 * n_boot))]]


def signflip_p(diffs, n_perm=N_PERM, seed=SEED):
    observed = abs(mean(diffs))
    rng = random.Random(seed)
    count = 0
    n = len(diffs)
    for _ in range(n_perm):
        value = abs(sum(diff if rng.random() < 0.5 else -diff for diff in diffs) / n)
        if value >= observed - 1e-15:
            count += 1
    return (count + 1) / (n_perm + 1)


def holm(pvalues):
    ordered = sorted(range(len(pvalues)), key=lambda index: pvalues[index])
    adjusted = [1.0] * len(pvalues)
    running = 0.0
    m = len(pvalues)
    for rank, index in enumerate(ordered):
        value = min(1.0, (m - rank) * pvalues[index])
        running = max(running, value)
        adjusted[index] = running
    return adjusted


def main():
    attempts = json.loads(ATTEMPTS.read_text(encoding="utf-8"))
    final = json.loads(FINAL.read_text(encoding="utf-8"))
    task_meta = {task["task_id"]: task for task in final["tasks"]}

    cells = defaultdict(list)
    for attempt in attempts:
        cells[(attempt["task_id"], attempt["condition"])].append(attempt)

    tasks = sorted(task_meta)
    means = {}
    for task in tasks:
        for condition in "ABC":
            rows = cells[(task, condition)]
            means[(task, condition)] = {
                metric: mean(float(row[metric]) for row in rows if row.get(metric) is not None)
                for metric in METRICS
            }

    output = {
        "schema_version": 1,
        "experiment": "mechanism-20-combined",
        "unit_of_analysis": "task",
        "n_tasks": len(tasks),
        "n_attempts": len(attempts),
        "bootstrap_resamples": N_BOOT,
        "permutation_resamples": N_PERM,
        "seed": SEED,
        "task_condition_means": {
            task_meta[task]["short"]: {
                condition: means[(task, condition)] for condition in "ABC"
            }
            for task in tasks
        },
        "contrasts": {},
    }

    for condition, reference in CONTRASTS:
        contrast = f"{condition}-{reference}"
        output["contrasts"][contrast] = {}
        for metric in METRICS:
            diffs = [
                means[(task, condition)][metric] - means[(task, reference)][metric]
                for task in tasks
                if means[(task, condition)][metric] is not None
                and means[(task, reference)][metric] is not None
            ]
            wins = sum(1 for diff in diffs if diff > 0)
            losses = sum(1 for diff in diffs if diff < 0)
            result = {
                "metric": metric,
                "n_pairs": len(diffs),
                "mean_diff": mean(diffs),
                "median_diff": statistics.median(diffs),
                "sd_diff": sd(diffs),
                "cohens_dz": mean(diffs) / sd(diffs) if sd(diffs) else None,
                "ci95_bootstrap": bootstrap_ci(diffs),
                "wins": wins,
                "losses": losses,
                "ties": len(diffs) - wins - losses,
                "sign_test_p": sign_test(wins, losses),
                "signflip_p": signflip_p(diffs),
                "rank_biserial": rank_biserial(diffs),
            }
            if metric in CONTINUOUS:
                try:
                    result["wilcoxon_p"] = float(wilcoxon(diffs, alternative="two-sided", method="auto").pvalue)
                except ValueError:
                    result["wilcoxon_p"] = None
            output["contrasts"][contrast][metric] = result

    # Holm adjustment for the C-B secondary endpoint family.
    secondary = [metric for metric in METRICS if metric != "resolved"]
    raw = [output["contrasts"]["C-B"][metric]["signflip_p"] for metric in secondary]
    adjusted = holm(raw)
    for metric, value in zip(secondary, adjusted):
        output["contrasts"]["C-B"][metric]["holm_p"] = value

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")
    print("C-B primary resolved")
    print(json.dumps(output["contrasts"]["C-B"]["resolved"], indent=2))
    print("C-B secondary")
    for metric in secondary:
        row = output["contrasts"]["C-B"][metric]
        print(
            metric,
            "diff=",
            round(row["mean_diff"], 4),
            "ci=",
            [round(x, 4) for x in row["ci95_bootstrap"]],
            "perm_p=",
            round(row["signflip_p"], 4),
            "holm=",
            round(row["holm_p"], 4),
            "wilcoxon=",
            round(row.get("wilcoxon_p"), 4) if row.get("wilcoxon_p") is not None else None,
            "dz=",
            round(row["cohens_dz"], 4) if row["cohens_dz"] is not None else None,
            "rb=",
            round(row["rank_biserial"], 4),
        )


if __name__ == "__main__":
    main()
