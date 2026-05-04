### 2026-05-04 — Extraction misclassified appointment scheduling as "other"

**Phase:** BUILD  
**What I tried:** Sent synthetic English ticket asking "Could you please tell me when my next maintenance is due?" with order reference and customer details. Expected `intent: appointment_scheduling`.

**What broke:** Model returned `intent: "other"`. Schema-valid, semantically wrong.

**Root cause:** System prompt defines tie-breaker rules ("pick highest-stakes if multi-intent") but does not define what each intent enum value actually means. With ambiguity in the ticket, the model defaults to "other" as a safe catch-all. The user prompt is correctly scoped to per-ticket data — the gap is in the system prompt's category definitions.

**Fix or mitigation:** Defer to v2. Add few-shot examples to system prompt — one canonical example per intent. Re-run on this ticket plus eval set to confirm.

**Generalizes to:** Enum-based classification with abstract rule definitions degrades to the safest category under ambiguity. Few-shot examples are not optional for ambiguous categories — they are the difference between schema-valid and schema-correct. The schema enforces structure; the prompt enforces meaning. The split between system prompt (stable rules) and user prompt (variable data) means category definitions belong only in the system prompt, not duplicated.

### 2026-05-04 — Scoring node rejected with "verbosity: low not supported"

**Phase:** BUILD  
**What I tried:** Configured scoring OpenAI node with verbosity option set to "low" to suppress reasoning output.

**What broke:** OpenAI returned 400 Bad Request: "Unsupported value: 'low' is not supported with the 'gpt-4.1-mini' model. Supported values are: 'medium'."

**Root cause:** Verbosity parameter is model-specific. gpt-4.1-mini only supports `medium`, while larger models accept `low` and `high`. The recommendation to use `low` came from an assumption that all models share the same options.

**Fix or mitigation:** Removed the verbosity option entirely. Under strict JSON schema output, verbosity has no effect anyway — the model can only emit schema-defined fields, no thinking-out-loud is possible. The option was redundant.

**Generalizes to:** Provider parameters are not uniform across models within the same provider's lineup. Always verify supported values against the specific model in use, not against a generic API documentation. The cheapest verification: send the request and read the rejection. Bad Request errors with explicit supported-values lists are gold — they teach you the actual constraint.
