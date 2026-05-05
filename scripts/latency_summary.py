#!/usr/bin/env python3
"""Quick latency summary across eval-result CSVs."""

import csv
import statistics
from pathlib import Path

CSVS = {
    "v1": "eval-results/eval_v1_20260505_092220.csv",
    "v2": "eval-results/eval_v1_20260505_105553.csv",
}

print(f"{'Version':<8} {'n':>4} {'min':>8} {'p50':>8} {'p95':>8} {'max':>8}  (ms)")
print("-" * 60)

for version, path in CSVS.items():
    if not Path(path).exists():
        print(f"{version}: file not found: {path}")
        continue
    
    latencies = []
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            # nur erfolgreiche Tickets in die Statistik
            if row["http_status"] == "200":
                latencies.append(int(row["latency_ms"]))
    
    if not latencies:
        print(f"{version}: no successful rows")
        continue
    
    latencies.sort()
    n = len(latencies)
    p50 = statistics.median(latencies)
    p95_idx = int(n * 0.95)
    p95 = latencies[min(p95_idx, n - 1)]
    
    print(f"{version:<8} {n:>4} {min(latencies):>8} {int(p50):>8} {p95:>8} {max(latencies):>8}")