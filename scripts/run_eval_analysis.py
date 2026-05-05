#!/usr/bin/env python3
"""
Eval-Analyse für Build 1 v1.
Joined Sheet-Output mit Ground Truth, berechnet Severity-Accuracy,
listet Failure-Patterns.
"""

import json
import csv
from collections import Counter
from pathlib import Path

# Pfade
SHEET_CSV = Path("eval-results/triage_output_v2.csv")
GROUND_TRUTH = Path("test-data/ground_truth.json")
REPORT_OUT = Path("eval-results/eval_v2_report.md")

# Ground Truth einlesen
with open(GROUND_TRUTH) as f:
    ground_truth = json.load(f)

# Sheet-Output einlesen
predictions = {}
with open(SHEET_CSV) as f:
    reader = csv.DictReader(f)
    for row in reader:
        ticket_id = row["ticket_id"].strip()
        predictions[ticket_id] = {
            "predicted_severity": row["severity"].strip().lower(),
            "confidence": float(row["confidence"]) if row["confidence"] else None,
            "reasoning": row["severity_reasoning"].strip(),
        }

# Join + Auswertung
results = []
for ticket_id, gt in ground_truth.items():
    expected = gt["expected_severity"].lower()
    pred = predictions.get(ticket_id)
    if not pred:
        results.append({
            "ticket_id": ticket_id,
            "expected": expected,
            "predicted": None,
            "match": False,
            "edge_case": gt.get("edge_case", ""),
            "reasoning": "MISSING from sheet output",
        })
        continue
    match = (pred["predicted_severity"] == expected)
    results.append({
        "ticket_id": ticket_id,
        "expected": expected,
        "predicted": pred["predicted_severity"],
        "match": match,
        "edge_case": gt.get("edge_case", ""),
        "reasoning": pred["reasoning"],
        "confidence": pred["confidence"],
    })

# Statistik
total = len(results)
correct = sum(1 for r in results if r["match"])
accuracy = correct / total if total else 0

# Confusion: erwartet → vorhergesagt
confusion = Counter()
for r in results:
    if r["predicted"] is not None:
        confusion[(r["expected"], r["predicted"])] += 1

# Failure-Liste
failures = [r for r in results if not r["match"]]

# Report ausgeben
print(f"\n{'='*60}")
print(f"BUILD 1 — EVAL v1 REPORT")
print(f"{'='*60}\n")
print(f"Total tickets:    {total}")
print(f"Correct:          {correct}")
print(f"Severity accuracy: {accuracy:.1%}\n")

print("Confusion matrix (expected → predicted):")
severities = ["low", "medium", "high", "critical"]
print(f"{'':12} " + " ".join(f"{s:>9}" for s in severities))
for exp in severities:
    row = f"{exp:12} "
    for pred in severities:
        count = confusion.get((exp, pred), 0)
        row += f"{count:>9} "
    print(row)
print()

print(f"Failures: {len(failures)}")
print("-" * 60)
for f_item in failures:
    print(f"\n{f_item['ticket_id']}")
    print(f"  Expected:  {f_item['expected']}")
    print(f"  Predicted: {f_item['predicted']}")
    print(f"  Edge case: {f_item['edge_case']}")
    if f_item.get('confidence') is not None:
        print(f"  Confidence: {f_item['confidence']}")
    print(f"  Reasoning: {f_item['reasoning'][:200]}")

# Markdown-Report für README/FAILURE_LOG
with open(REPORT_OUT, "w") as f:
    f.write("# Build 1 — Eval v1 Report\n\n")
    f.write(f"**Total:** {total}  \n")
    f.write(f"**Correct:** {correct}  \n")
    f.write(f"**Severity accuracy:** {accuracy:.1%}\n\n")
    f.write("## Confusion Matrix (expected → predicted)\n\n")
    f.write("| | " + " | ".join(severities) + " |\n")
    f.write("|" + "---|" * (len(severities) + 1) + "\n")
    for exp in severities:
        row = f"| **{exp}** |"
        for pred in severities:
            row += f" {confusion.get((exp, pred), 0)} |"
        f.write(row + "\n")
    f.write(f"\n## Failures ({len(failures)})\n\n")
    for fi in failures:
        f.write(f"### {fi['ticket_id']}\n")
        f.write(f"- **Expected:** {fi['expected']}\n")
        f.write(f"- **Predicted:** {fi['predicted']}\n")
        f.write(f"- **Edge case:** {fi['edge_case']}\n")
        if fi.get('confidence') is not None:
            f.write(f"- **Confidence:** {fi['confidence']}\n")
        f.write(f"- **Reasoning:** {fi['reasoning']}\n\n")

print(f"\n✅ Report saved: {REPORT_OUT}")