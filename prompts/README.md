# Prompts

Version-controlled copies of the LLM prompts used in the n8n workflow.
The workflow itself holds the canonical copies in the OpenAI nodes; these
files mirror them for diff-ability and history (n8n Cloud version history
is limited to 1 day on the current plan).

## Files
- `extraction_v1.txt` — extraction LLM system prompt (unchanged v1→v2)
- `scoring_v1.txt` — scoring LLM system prompt, v1 baseline
- `scoring_v2.txt` — scoring LLM system prompt, v2

## v1 → v2 scoring diff (what changed)
1. **Authority Hierarchy** added — objective system state is authoritative,
   customer urgency framing is informative only.
2. **Three few-shot examples** added — calmly-critical, escalation-risk,
   early-warning.
3. **medium definition** split into (a) functional degradation and
   (b) routine-with-escalation-risk.
4. **low definition** tightened — both "no escalation risk" AND "no
   functional impact" must hold.

Extraction prompt is identical across v1 and v2, so any eval difference
is attributable to the scoring prompt alone.