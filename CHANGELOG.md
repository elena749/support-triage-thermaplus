# Changelog

## 2026-05-04

- Webhook trigger configured at path `support-triage-v1`. Receives synthetic ThermaPlus ticket payloads via curl.
- Extraction LLM node added (OpenAI `gpt-4.1-mini`, temperature 0, JSON Schema-enforced via Output Format).
- System prompt locks extraction-only role; user message templates from Webhook payload.
- First end-to-end test successful: German emergency ticket extracted to schema-valid JSON in single call.

- Scoring LLM node added (gpt-4.1-mini, temperature 0, JSON Schema-enforced).
- End-to-end test of two-LLM pipeline successful: Müller emergency ticket (heating off, two children) classified as severity=critical, confidence=0.95, with German reasoning string.
  
- Tier multiplier code node added. Combines scoring output with original webhook payload, calculates final_priority = severity_score × tier_weight using deterministic JavaScript logic.
- First complete pipeline run: Müller emergency ticket (Tier C) → severity critical → final_priority 5.6.

- Scoring system prompt extended with German heating-domain context: heating season corridor (Oct 1 – Apr 30 per case law), outdoor-temperature thresholds by building energy class (11°C low-energy, 17°C unrenovated old-build), vulnerable-occupant override, safety-signal override, multi-property B2B escalation rule.
- Code node extended with deterministic season multiplier: 1.0 in heating season, 0.7 outside. Applied as third factor in final_priority calculation alongside severity_score and tier_weight.
- Sheet schema extended with in_heating_season (bool) and season_multiplier (float) columns.
- Verified end-to-end on Müller ticket dated April 30: critical + Tier C + heating season → final_priority 5.6, in_heating_season TRUE.
- 30 synthetic eval tickets brainstormed in test-data/tickets_brainstorm.md, covering severity distribution (6/8/10/6), language mix (21 DE / 6 EN / 3 mixed), customer types, tiers, channels, and 16 explicit edge case categories including prompt injection.
- Workflow v1 exported to n8n/workflow_v1.json.

  ## [v1.0-eval] — 2026-05-05
- v1 evaluation completed against 30-ticket held-out set
- Severity accuracy: 76.7% (23/30)
- Failure patterns identified — see FAILURE_LOG.md (2026-05-05)
- v2 mitigations planned: few-shot examples in scoring prompt
