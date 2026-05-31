#!/usr/bin/env python3
"""
run_multi_eval.py — Multi-run evaluation of scoring prompt v1 vs v2.

WHY: The v1->v2 comparison was a single run over 30 tickets (n=1). A 3.3pp
difference is one ticket. LLMs are not byte-deterministic even at temperature 0,
so a single run cannot tell us whether v2 is genuinely better or just noise.
This runs each version N times, computes mean +/- stddev of severity accuracy,
and reports whether the two versions' ranges overlap (overlap => within noise).

MEASUREMENT: severity accuracy = fraction where predicted == expected. This is a
deterministic string comparison in code — no LLM judge, because severity is a
closed 4-value label space with an exact correct answer.

PIPELINE PER TICKET: extraction call -> scoring call -> compare to ground truth.
Evaluates the PROMPTS via the OpenAI API; bypasses n8n and the deterministic
tier/season multiplier (identical across versions). Extraction prompt is the
same for v1 and v2, so any delta is attributable to the scoring prompt.
"""

import os
import json
import glob
import statistics
from datetime import datetime
from openai import OpenAI

# --- CONFIG ---
MODEL = "gpt-4.1-mini"
N_RUNS = 5
TEMPERATURE = 0
TICKETS_DIR = "test-data/tickets"
GROUND_TRUTH = "test-data/ground_truth.json"
PROMPTS_DIR = "prompts"
OUTPUT_DIR = "eval-results"
VALID_SEVERITIES = ["low", "medium", "high", "critical"]

EXTRACTION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["ticket_id", "language", "intent", "product_area",
                 "sentiment", "entities", "summary_de", "summary_en"],
    "properties": {
        "ticket_id": {"type": "string"},
        "language": {"type": "string", "enum": ["de", "en", "other"]},
        "intent": {"type": "string", "enum": [
            "breakdown_emergency", "repair_request", "appointment_scheduling",
            "appointment_confirmation", "billing_question", "warranty_claim",
            "quote_request", "complaint", "other"]},
        "product_area": {"type": "string", "enum": [
            "heating_system", "heat_pump", "service_contract", "billing", "unknown"]},
        "sentiment": {"type": "string", "enum": ["negative", "neutral", "positive"]},
        "entities": {
            "type": "object",
            "additionalProperties": False,
            "required": ["addresses", "phone_numbers", "order_ids", "error_codes"],
            "properties": {
                "addresses": {"type": "array", "items": {"type": "string"}},
                "phone_numbers": {"type": "array", "items": {"type": "string"}},
                "order_ids": {"type": "array", "items": {"type": "string"}},
                "error_codes": {"type": "array", "items": {"type": "string"}},
            },
        },
        "summary_de": {"type": "string"},
        "summary_en": {"type": "string"},
    },
}

SCORING_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["ticket_id", "severity", "severity_reasoning", "confidence"],
    "properties": {
        "ticket_id": {"type": "string"},
        "severity": {"type": "string", "enum": VALID_SEVERITIES},
        "severity_reasoning": {"type": "string"},
        "confidence": {"type": "number"},
    },
}


def load_prompt(filename):
    with open(os.path.join(PROMPTS_DIR, filename), "r", encoding="utf-8") as f:
        return f.read().strip()


def load_tickets():
    tickets = []
    for path in sorted(glob.glob(os.path.join(TICKETS_DIR, "*.json"))):
        with open(path, "r", encoding="utf-8") as f:
            tickets.append(json.load(f))
    return tickets


def call_llm(client, system_prompt, user_content, schema, schema_name, max_tokens):
    resp = client.chat.completions.create(
        model=MODEL,
        temperature=TEMPERATURE,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {"name": schema_name, "schema": schema, "strict": True},
        },
    )
    return json.loads(resp.choices[0].message.content)


def run_one_ticket(client, ticket, extraction_prompt, scoring_prompt):
    extraction_user = (
        f"Process this ticket and extract structured fields.\n\n"
        f"ticket_id: {ticket['ticket_id']}\n"
        f"subject: {ticket['subject']}\n"
        f"body:\n{ticket['body']}"
    )
    extracted = call_llm(client, extraction_prompt, extraction_user,
                         EXTRACTION_SCHEMA, "extraction_output", 2000)
    scoring_user = f"Score the severity of this triaged ticket:\n\n{json.dumps(extracted, ensure_ascii=False, indent=2)}"
    scored = call_llm(client, scoring_prompt, scoring_user,
                      SCORING_SCHEMA, "scoring_output", 500)
    return scored["severity"]


def evaluate_version(client, version_label, scoring_prompt, extraction_prompt,
                     tickets, ground_truth, rows):
    accuracies = []
    ticket_correct_count = {t["ticket_id"]: 0 for t in tickets}
    for run in range(1, N_RUNS + 1):
        correct = 0
        for ticket in tickets:
            tid = ticket["ticket_id"]
            expected = ground_truth[tid]["expected_severity"]
            try:
                predicted = run_one_ticket(client, ticket, extraction_prompt, scoring_prompt)
            except Exception as e:
                predicted = f"ERROR:{type(e).__name__}"
            is_correct = int(predicted == expected)
            correct += is_correct
            ticket_correct_count[tid] += is_correct
            rows.append({
                "version": version_label, "run": run, "ticket_id": tid,
                "predicted": predicted, "expected": expected,
                "correct": is_correct,
                "edge_case": ground_truth[tid].get("edge_case", ""),
            })
        acc = correct / len(tickets) * 100
        accuracies.append(acc)
        print(f"  {version_label} run {run}/{N_RUNS}: {correct}/{len(tickets)} = {acc:.1f}%")
    return accuracies, ticket_correct_count


def summarize(label, accuracies):
    mean = statistics.mean(accuracies)
    stdev = statistics.stdev(accuracies) if len(accuracies) > 1 else 0.0
    lo, hi = mean - stdev, mean + stdev
    print(f"\n{label}: mean={mean:.1f}%  stddev={stdev:.1f}%  "
          f"range=[{lo:.1f}%, {hi:.1f}%]  (runs: {[f'{a:.1f}' for a in accuracies]})")
    return {"mean": mean, "stdev": stdev, "lo": lo, "hi": hi, "runs": accuracies}


def main():
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY not set. Run: export OPENAI_API_KEY=sk-...")
    client = OpenAI()

    with open(GROUND_TRUTH, "r", encoding="utf-8") as f:
        ground_truth = json.load(f)
    tickets = load_tickets()
    extraction_prompt = load_prompt("extraction_v1.txt")
    scoring_v1 = load_prompt("scoring_v1.txt")
    scoring_v2 = load_prompt("scoring_v2.txt")

    print(f"Model: {MODEL} | Tickets: {len(tickets)} | Runs per version: {N_RUNS}")
    print(f"Total API calls: {2 * N_RUNS * len(tickets) * 2}\n")

    rows = []
    print("=== Scoring v1 ===")
    v1_acc, v1_stab = evaluate_version(client, "v1", scoring_v1, extraction_prompt,
                                       tickets, ground_truth, rows)
    print("\n=== Scoring v2 ===")
    v2_acc, v2_stab = evaluate_version(client, "v2", scoring_v2, extraction_prompt,
                                       tickets, ground_truth, rows)

    print("\n" + "=" * 60)
    v1_sum = summarize("v1", v1_acc)
    v2_sum = summarize("v2", v2_acc)
    overlap = v1_sum["hi"] >= v2_sum["lo"] and v2_sum["hi"] >= v1_sum["lo"]
    print("\n" + "-" * 60)
    if overlap:
        print("RESULT: Ranges OVERLAP. The v1/v2 difference is within measurement "
              "noise at n=30. NOT resolvable as a real improvement.")
    else:
        print("RESULT: Ranges do NOT overlap. v2 difference is outside noise — "
              "a resolvable improvement at n=30.")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    csv_path = os.path.join(OUTPUT_DIR, f"multi_run_{ts}.csv")
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("version,run,ticket_id,predicted,expected,correct,edge_case\n")
        for r in rows:
            ec = r["edge_case"].replace(",", ";")
            f.write(f'{r["version"]},{r["run"]},{r["ticket_id"]},'
                    f'{r["predicted"]},{r["expected"]},{r["correct"]},{ec}\n')
    print(f"\nPer-row results: {csv_path}")

    stab_path = os.path.join(OUTPUT_DIR, f"per_ticket_stability_{ts}.csv")
    with open(stab_path, "w", encoding="utf-8") as f:
        f.write("ticket_id,edge_case,v1_correct_of_runs,v2_correct_of_runs,n_runs\n")
        for t in tickets:
            tid = t["ticket_id"]
            ec = ground_truth[tid].get("edge_case", "").replace(",", ";")
            f.write(f'{tid},{ec},{v1_stab[tid]},{v2_stab[tid]},{N_RUNS}\n')
    print(f"Per-ticket stability: {stab_path}")

    summary_path = os.path.join(OUTPUT_DIR, f"multi_run_summary_{ts}.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump({"model": MODEL, "n_runs": N_RUNS, "n_tickets": len(tickets),
                   "temperature": TEMPERATURE, "v1": v1_sum, "v2": v2_sum,
                   "ranges_overlap": overlap, "timestamp": ts}, f, indent=2)
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()