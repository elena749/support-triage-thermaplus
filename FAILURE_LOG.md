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

### 2026-05-04 — Code node failed: "Unknown severity value: undefined"

**Phase:** BUILD  
**What I tried:** Tier multiplier code node reading `$input.item.json.severity` to look up severity score and calculate final_priority.

**What broke:** Node threw "Unknown severity value: undefined" on every test run. Pipeline stopped before tier multiplication.

**Root cause:** OpenAI Responses API (enabled via `Use Responses API` toggle in n8n) returns a wrapped envelope: `{ id, object, output: [{ content: [{ text: { severity, ... } }] }] }`. The actual schema fields live at `output[0].content[0].text.*`, not at the root. Same payload shape, different access path than the legacy Chat Completions API.

**Fix or mitigation:** Updated code node to read `raw.output[0].content[0].text` instead of `raw`. The wrapper is provider-API-specific and would need to be adjusted if migrating between Responses API and Chat Completions API.

**Generalizes to:** API response shapes are part of the integration contract — even within a single provider, different API endpoints produce different envelopes around the same payload. Schema validation enforces structure inside the payload; it does not normalize the wrapper around it. Always inspect the raw response shape before writing access code. The defensive validation (`throw new Error`) caught the issue cleanly instead of silently producing NaN downstream — that's the value of fail-fast.

## 2026-05-05 — v1 Eval: systematische Unterschätzung durch 
Kunden-Selbsteinschätzung

**Was ich tat:** Eval-Run gegen 30 Ground-Truth-Tickets, Severity-Accuracy 
und Confusion Matrix berechnet.

**Was brach:** 7/30 Tickets falsch klassifiziert, 6 davon eine Stufe zu 
mild. Auffälligstes Beispiel: TH-04535 — Heizung ausgefallen, aber Kunde 
sagt "nicht dringend". Pipeline rated medium, Ground Truth high. 
Reasoning des LLM: "Kunde gibt an, dass es nicht dringend ist."

**Root cause:** Scoring-Prompt enthielt keine explizite Regel zur 
Gewichtung von Kunden-Selbsteinschätzung gegenüber objektivem 
System-Zustand. LLM hat Kundenaussage als Authority interpretiert, 
nicht als Signal.

**Fix in v2:** Few-Shot-Beispiele im Scoring-Prompt, die genau diesen 
Anti-Pattern abdecken (Kunde framed mild, objektiver Zustand ist 
schwerwiegend → score by objective state).

**Generalisiert zu:** LLMs übernehmen tonale Signale ungeprüft, wenn 
der Prompt keine Hierarchie zwischen Datenquellen vorgibt. Bei 
Triage/Klassifikation muss explizit definiert werden, welche Signale 
*authoritative* sind (objektiver Zustand, deterministische Felder) 
und welche nur *informative* sind (Kunden-Tonalität, 
Selbsteinschätzung). Sonst kalibriert das System nach dem lautesten 
oder höflichsten Signal — nicht nach dem relevantesten.

Ticket-File-Names entkoppelt von Ticket-IDs. Beim Testen einzelner Failures muss erst gesucht werden welches File welchen Ticket-Identifier hat. Generalisiert zu: Test-Daten brauchen einen Index oder eine Naming-Convention, die das Mapping trivial macht — sonst kostet jede Debug-Session Such-Aufwand. Für nächste Builds: Test-Files mit dem Identifier im Filename benennen (z.B. ticket_TH-04535.json).

## 2026-05-05 — Eval-Run-Ziel vor Start nicht separiert

**Was ich tat:** v2-Eval-Run gestartet, ohne den Triage-Tab im Google 
Sheet vorher zu leeren oder zu duplizieren. v1- und v2-Ergebnisse 
landen im selben Tab, in derselben Spalten-Struktur, untereinander.

**Was brach:** Saubere Trennung v1 vs v2 für die Auswertung war nicht 
mehr möglich ohne manuelles Sortieren. Hätte Zeitersparnis von 
2 Minuten Pre-Setup gegen 5 Minuten Post-Cleanup eingetauscht.

**Root cause:** Eval-Disziplin schreibt vor: vor jedem Run das 
Output-Ziel definieren. In der Aufregung des "v2 hat den 
Single-Test bestanden, Run starten!" übersehen.

**Fix:** Sheet nachträglich aufgeräumt — Tab dupliziert, v1 in 
Archive, v2 im Original-Tab.

**Generalisiert zu:** Bei jedem Eval-Run sind drei Setup-Punkte vor 
dem Start zu klären, nicht währenddessen oder danach: (1) Wohin 
schreiben die Outputs? (2) Wie unterscheide ich diesen Run von 
vorherigen? (3) Was ist die Roll-back-Strategie, falls der Run 
schiefgeht oder Daten überschreibt? Pre-Run-Checkliste spart 
Post-Run-Cleanup.

## 2026-05-05 — Rate limit surfacing only at batch volume

**What I did:** Ran v2 eval batch (30 tickets via curl loop with 1-sec 
spacing). Single-ticket tests during prompt iteration had all worked.

**What broke:** Ticket 30 returned HTTP 500. n8n execution log: 
"Problem in node 'Append row in sheet': The service is receiving too 
many requests from you." — Google Sheets API rate limit (60 writes/
minute/user).

**Root cause:** Pipeline had no retry policy on the Sheets Append 
node. Single-ticket smoke tests passed because they never approached 
the rate limit. Batch volume surfaced the missing resilience.

**Fix:** Enabled "Retry on Fail" on the Sheets Append node (3 tries, 
2000ms between). Mitigation lives at the failure point — not 
prophylactically in the caller.

**Generalizes to:** "It worked at low volume" is not evidence a 
pipeline is safe. Rate limits, throttling, and transient API errors 
surface only under load. Any external-service write needs an explicit 
retry policy as a default — not as an optimization. Smoke tests 
deceive when the real risk is volume-dependent.

## 2026-05-05 — v2 prompt iteration: small accuracy gain, mitigations did not stick

**What I did:** Built v2 of the scoring prompt with three concrete mitigations targeted at v1 failure patterns: an Authority Hierarchy section (objective state > customer framing), a sharpened low/medium boundary covering escalation-risk inquiries, and three in-prompt few-shot examples derived from v1 failures. Reran the full 30-ticket eval against the same ground truth.

**What broke:** v2 fixed only 1 of 7 v1 failures (the "angry customer no emergency" case). The remaining six failures persisted, with reasoning patterns close to v1. For at least one persistent case, a single-ticket smoke test had returned the correct severity in isolation, but the batch eval produced the wrong one — same prompt, same temperature=0, different output.

**Root cause:** Two effects compounding.
1. LLM outputs are not byte-deterministic even at temperature=0. OpenAI does not guarantee reproducibility, so a single correct output is not evidence of a working mitigation.
2. Prompt-level instruction is probabilistic, not gate-based. Where the model carries a strong learned prior ("customer says not urgent" → de-escalate), nudging via rules and examples shifts the distribution but does not switch behavior reliably.

**Fix:** Documented the result honestly in the README (v2 eval section). Did not iterate prompt further — diminishing returns and overfitting risk against a 30-ticket set. v3 hypothesis: move from prompt-level instruction to architectural pattern (two-stage verification with a second LLM pass).

**Generalizes to:** When evaluating LLM-based systems, n=1 is not enough. A single batch run cannot distinguish prompt weakness from inherent model variance. Meaningful before/after comparisons require multi-run evaluation (3-5 runs per version, mean ± stddev). Otherwise small accuracy gains may be noise. This applies to any prompt-iteration claim of the form "v2 is X% better than v1" — the claim is not credible without variance bounds.

## 2026-05-05 — Google Sheets rate limit surfacing only at batch volume

**What I did:** Ran the v2 eval batch (30 tickets via curl loop with 1-second spacing). Single-ticket smoke tests during prompt iteration had all worked.

**What broke:** Ticket 30 returned HTTP 500. The n8n execution log showed: "Problem in node 'Append row in sheet': The service is receiving too many requests from you." Google Sheets API enforces a rate limit of 60 writes per minute per user. At one curl per second plus n8n's internal sheet operations, the threshold was crossed near the end of the run.

**Root cause:** The pipeline had no retry policy on the Sheets append node. Smoke tests passed because they never approached the rate limit. Batch volume surfaced the missing resilience.

**Fix:** Enabled "Retry on Fail" on the Sheets Append node in n8n (3 tries, 2000ms wait between). Mitigation lives at the failure point — at the Sheets node — rather than prophylactically in the caller (the bash script). Re-sent ticket 30 individually; passed.

**Generalizes to:** "It worked at low volume" is not evidence a pipeline is safe. Rate limits, throttling, and transient API errors surface only under load — they are invisible during single-ticket development. Any external-service write needs an explicit retry policy as a default, not as an optimization. Smoke tests deceive when the real risk is volume-dependent.
