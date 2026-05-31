#!/usr/bin/env python3
"""
confusion_matrix.py — Build confusion matrices from multi-run eval CSV.

Reads the per-row results (version, run, ticket_id, predicted, expected, correct)
and prints a confusion matrix per version: rows = true severity (expected),
columns = predicted severity. Diagonal = correct; off-diagonal = error patterns.

Aggregates across all runs, so each cell counts all (ticket x run) predictions.
No API calls — pure analysis of existing eval output.
"""

import sys
import csv
from collections import defaultdict

LEVELS = ["low", "medium", "high", "critical"]


def load_rows(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append(r)
    return rows


def build_matrix(rows, version):
    # matrix[expected][predicted] = count
    matrix = {t: defaultdict(int) for t in LEVELS}
    skipped = 0
    for r in rows:
        if r["version"] != version:
            continue
        exp, pred = r["expected"], r["predicted"]
        if exp not in LEVELS or pred not in LEVELS:
            skipped += 1   # e.g. ERROR: rows
            continue
        matrix[exp][pred] += 1
    return matrix, skipped


def print_matrix(matrix, version):
    print(f"\n=== Confusion matrix — {version} (rows=expected, cols=predicted) ===")
    header = "expected \\ pred | " + " | ".join(f"{l:>8}" for l in LEVELS) + " |  total | acc"
    print(header)
    print("-" * len(header))
    grand_correct = 0
    grand_total = 0
    for exp in LEVELS:
        row_total = sum(matrix[exp][p] for p in LEVELS)
        correct = matrix[exp][exp]
        grand_correct += correct
        grand_total += row_total
        acc = (correct / row_total * 100) if row_total else 0.0
        cells = " | ".join(f"{matrix[exp][p]:>8}" for p in LEVELS)
        print(f"{exp:>15} | {cells} | {row_total:>6} | {acc:5.1f}%")
    overall = (grand_correct / grand_total * 100) if grand_total else 0.0
    print("-" * len(header))
    print(f"Overall accuracy: {grand_correct}/{grand_total} = {overall:.1f}%")


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "eval-results/multi_run_20260531_100719.csv"
    rows = load_rows(path)
    for version in ["v1", "v2"]:
        matrix, skipped = build_matrix(rows, version)
        print_matrix(matrix, version)
        if skipped:
            print(f"(skipped {skipped} non-standard rows, e.g. ERROR entries)")


if __name__ == "__main__":
    main()
    