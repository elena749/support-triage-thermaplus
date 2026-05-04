# Changelog

## 2026-05-04

- Webhook trigger configured at path `support-triage-v1`. Receives synthetic ThermaPlus ticket payloads via curl.
- Extraction LLM node added (OpenAI `gpt-4.1-mini`, temperature 0, JSON Schema-enforced via Output Format).
- System prompt locks extraction-only role; user message templates from Webhook payload.
- First end-to-end test successful: German emergency ticket extracted to schema-valid JSON in single call.
