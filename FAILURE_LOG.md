# Failure Log — Build 1

Phase / What I tried / What broke / Root cause / Fix or mitigation / Generalizes to.

---

## 2026-05-04 — Extraction misclassified appointment scheduling as "other"

**Phase:** BUILD
**What I tried:** Sent synthetic English ticket asking "Could you please tell me when my next maintenance is due?" with order reference and customer details. Expected `intent: appointment_scheduling`.

**What broke:** Model returned `intent: "other"`. Schema-valid, semantically wrong.

**Root cause:** System prompt defines tie-breaker rules ("pick highest-stakes if multi-intent") but does not define what each intent enum value actually means. With ambiguity in the ticket, the model defaults to "other" as a safe catch-all.

**Fix:** Defer to v2. Add few-shot examples to system prompt, one canonical example per intent.

**Generalizes to:** Enum-based classification with abstract rule definitions degrades to the safest category under ambiguity. Few-shot examples are not optional for ambiguous categories: they are the difference between schema-valid and schema-correct. The schema enforces structure; the prompt enforces meaning.

---

## 2026-05-04 — Scoring node rejected with "verbosity: low not supported"

**Phase:** BUILD
**What I tried:** Configured scoring OpenAI node with verbosity option set to "low" to suppress reasoning output.

**What broke:** OpenAI returned 400 Bad Request: "Unsupported value: 'low' is not supported with the 'gpt-4.1-mini' model. Supported values are: 'medium'."

**Root cause:** Verbosity parameter is model-specific. gpt-4.1-mini only supports `medium`, while larger models accept `low` and `high`.

**Fix:** Removed the verbosity option entirely. Under strict JSON schema output, verbosity has no effect anyway, the model can only emit schema-defined fields.

**Generalizes to:** Provider parameters are not uniform across models within the same provider. Always verify supported values against the specific model in use, not against a generic API documentation. Bad Request errors with explicit supported-values lists are gold: they teach you the actual constraint.

---

## 2026-05-04 — Code node failed: "Unknown severity value: undefined"

**Phase:** BUILD
**What I tried:** Tier multiplier code node reading `$input.item.json.severity` to look up severity score and calculate final_priority.

**What broke:** Node threw "Unknown severity value: undefined" on every test run. Pipeline stopped before tier multiplication.

**Root cause:** OpenAI Responses API (enabled via `Use Responses API` toggle in n8n) returns a wrapped envelope: `{ id, object, output: [{ content: [{ text: { severity, ... } }] }] }`. The actual schema fields live at `output[0].content[0].text.*`, not at the root.

**Fix:** Updated code node to read `raw.output[0].content[0].text` instead of `raw`.

**Generalizes to:** API response shapes are part of the integration contract. Even within a single provider, different API endpoints produce different envelopes around the same payload. Schema validation enforces structure inside the payload; it does not normalize the wrapper around it. Always inspect the raw response shape before writing access code. The fail-fast validation (`throw new Error`) caught the issue cleanly instead of silently producing NaN downstream.

---

## 2026-05-05 — v1 Eval: systematic underestimation via customer self-assessment

**Phase:** EVAL
**What I tried:** Eval run against 30 ground-truth tickets, computing severity accuracy and confusion matrix.

**What broke:** 7/30 tickets misclassified, 6 of them one level too mild. Most striking: TH-04535, heating fully out, customer says "not urgent". Pipeline rated medium, ground truth high. LLM reasoning: "Customer states it is not urgent."

**Root cause:** Scoring prompt contained no explicit rule about weighting customer self-assessment against objective system state. The LLM treated the customer's statement as authoritative rather than as one signal among others.

**Fix in v2:** Few-shot examples in the scoring prompt covering exactly this anti-pattern (customer frames mild, objective state is severe, score by objective state).

**Generalizes to:** LLMs absorb tonal signals unchecked when the prompt does not impose a hierarchy among data sources. For classification tasks consuming natural-language input, the prompt must explicitly define which signals are *authoritative* (objective state, deterministic fields) and which are merely *informative* (customer tone, self-assessment). Otherwise, the system calibrates by the loudest or politest signal, not the most relevant.

---

## 2026-05-05 — Test data: ticket file names decoupled from ticket IDs

**Phase:** EVAL
**What I tried:** Tested a single failing ticket (TH-2026-04535) by guessing the corresponding file name (`ticket_005.json`).

**What broke:** File name and ticket ID don't share a mapping. Had to grep through the test-data directory to find which file contained which ticket ID.

**Root cause:** Test data generator assigned filenames sequentially (`ticket_001.json` to `ticket_030.json`) but ticket IDs were assigned independently in the JSON content (e.g. TH-2026-04321, TH-2026-04532). No index or naming convention bridged the two.

**Fix:** Used `grep -rl "TH-2026-XXXXX" test-data/tickets/` to find the file. For future builds: name test files with the identifier embedded (e.g. `ticket_TH-04535.json`).

**Generalizes to:** Test data needs a naming convention or index that makes the mapping from identifier to artifact trivial. Otherwise every debug session pays a search tax. Reproducibility is not just about deterministic outputs, it is also about being able to find the inputs.

---

## 2026-05-05 — Eval run target not separated before start

**Phase:** EVAL
**What I tried:** Started v2 eval run without first clearing or duplicating the Triage tab in the Google Sheet. v1 and v2 results landed in the same tab, same column structure, stacked.

**What broke:** Clean separation of v1 vs v2 for analysis was no longer possible without manual sorting. Traded 2 minutes of pre-setup for 5 minutes of post-cleanup.

**Root cause:** Eval discipline says: define the output target before the run. In the rush of "v2 passed the single-ticket test, start the run," missed it.

**Fix:** Cleaned up the sheet retroactively. Duplicated the tab, archived v1, kept v2 in the live tab.

**Generalizes to:** Every eval run needs three setup points clarified *before* start, not during or after: (1) Where do outputs go? (2) How do I distinguish this run from prior ones? (3) What is the rollback path if the run misfires or overwrites data? A pre-run checklist is cheaper than post-run cleanup.

---

## 2026-05-05 — v2 prompt iteration: small accuracy gain, mitigations did not stick

**Phase:** EVAL
**What I tried:** Built v2 of the scoring prompt with three mitigations targeted at v1 failure patterns: Authority Hierarchy section (objective state outranks customer framing), sharpened low/medium boundary covering escalation-risk inquiries, three in-prompt few-shot examples derived from v1 failures. Reran the full 30-ticket eval.

**What broke:** v2 fixed only 1 of 7 v1 failures (TH-04559, angry customer with no functional emergency). The other six persisted, with reasoning patterns close to v1. For at least one persistent case, a single-ticket smoke test had returned the correct severity in isolation, but the batch eval produced the wrong one. Same prompt, same temperature=0, different output.

**Root cause:** Two effects compounding.
1. LLM outputs are not byte-deterministic even at temperature=0. OpenAI does not guarantee reproducibility, so a single correct output is not evidence of a working mitigation.
2. Prompt-level instruction is probabilistic, not gate-based. Where the model carries a strong learned prior ("customer says not urgent" → de-escalate), nudging via rules and examples shifts the distribution but does not switch behavior reliably.

**Fix:** Documented the result honestly in the README. Did not iterate prompt further: diminishing returns and overfitting risk against a 30-ticket set. v3 hypothesis: move from prompt-level instruction to architectural pattern (two-stage verification with a second LLM pass).

**Generalizes to:** When evaluating LLM-based systems, n=1 is not enough. A single batch run cannot distinguish prompt weakness from inherent model variance. Meaningful before/after comparisons require multi-run evaluation (3-5 runs per version, mean ± stddev). Any prompt-iteration claim of the form "v2 is X% better than v1" is not credible without variance bounds.

---

## 2026-05-05 — Google Sheets rate limit surfacing only at batch volume

**Phase:** EVAL
**What I tried:** Ran the v2 eval batch (30 tickets via curl loop with 1-second spacing). Single-ticket smoke tests during prompt iteration had all worked.

**What broke:** Ticket 30 returned HTTP 500. The n8n execution log showed: "Problem in node 'Append row in sheet': The service is receiving too many requests from you." Google Sheets API enforces a rate limit of 60 writes per minute per user. At one curl per second plus n8n's internal sheet operations, the threshold was crossed near the end of the run.

**Root cause:** The pipeline had no retry policy on the Sheets append node. Smoke tests passed because they never approached the rate limit. Batch volume surfaced the missing resilience.

**Fix:** Enabled "Retry on Fail" on the Sheets Append node in n8n (3 tries, 2000ms wait between). Mitigation lives at the failure point, the Sheets node, rather than prophylactically in the caller (the bash script). Re-sent ticket 30 individually; passed.

**Generalizes to:** "It worked at low volume" is not evidence a pipeline is safe. Rate limits, throttling, and transient API errors surface only under load: they are invisible during single-ticket development. Any external-service write needs an explicit retry policy as a default, not as an optimization. Smoke tests deceive when the real risk is volume-dependent.

2026-05-28 — Webhook input contract was too narrow for downstream business logic

Phase: BUILD
What I tried: Tested the support-triage webhook with a minimal payload containing only the obvious customer message fields.
What broke: The deterministic scoring node failed because customer_tier and received_at were missing, even though extraction and scoring had already succeeded.
Root cause: I had implicitly moved business-context fields out of the input contract, but the downstream priority calculation still depended on them.
Fix or mitigation: Put customer_tier, received_at, and related business-context fields back into the webhook contract and validate them explicitly at the input stage.
Generalizes to: Business logic should not depend on fields that are only “sometimes present.” If a field is required for routing, scoring, or compliance, it belongs in the input contract and should fail early when absent.
2026-05-28 — LLM output wrapper caused field lookups to fail

Phase: BUILD
What I tried: Read scoring output directly from the Code node input as if it were the parsed object.
What broke: The code node threw Unknown severity value: undefined because the actual fields were nested inside output[0].content[0].text.
Root cause: The Responses API returned a wrapper envelope around the schema output, and the code assumed the payload lived at the root.
Fix or mitigation: Update the code node to read the nested text object explicitly before applying deterministic logic.
Generalizes to: Schema validation does not eliminate response-shape handling. Integration code still has to navigate provider-specific envelopes correctly.
2026-05-28 — False-path validation revealed response branching was incomplete

Phase: BUILD
What I tried: Triggered the invalid-input branch on purpose using an incomplete webhook payload.
What broke: The false path had not yet been verified, so the workflow risked returning a default response instead of a deliberate error payload.
Root cause: I had validated the success path first and only later checked whether the failure branch actually produced a response.
Fix or mitigation: Test the false branch explicitly with a missing-field payload and confirm the Respond to Webhook node returns a 422 with structured validation errors.
Generalizes to: A workflow is not production-safe until both success and failure branches are exercised. “Happy path works” is not enough for webhook systems.
2026-05-28 — Success path returned empty because response node was missing after scoring

Phase: BUILD
What I tried: Ran the workflow after scoring succeeded, expecting the webhook to return the result automatically.
What broke: The workflow returned HTTP 200 with an empty body.
Root cause: The success branch reached the scoring node, but there was no final response node on that path, so n8n fell back to a default empty 200 response.
Fix or mitigation: Add an explicit final response node after the success branch, or normalize the output first and then respond from that node.
Generalizes to: In webhook workflows, execution success and response success are separate concerns. A workflow can complete internally while still failing to return useful output to the caller.
One more strong lesson
2026-05-28 — The input contract drifted while iterating

Phase: BUILD
What I tried: Simplified the test payload during debugging to focus on the ticket text.
What broke: The workflow became less robust because the business fields needed later were no longer present in the payload.
Root cause: Debugging convenience accidentally changed the shape of the real contract.
Fix or mitigation: Keep the full contract in the webhook payload, and use separate test cases to verify missing-field behavior instead of shrinking the canonical input.
Generalizes to: Debug payloads are not the same thing as production contracts. If you test with reduced input, you must still preserve the real required fields somewhere in the workflow design.