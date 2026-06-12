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

## 2026-05-28T11:08 — Subworkflow Webhook Refactor

**Phase:** Refactor (architecture)
**What I tried:** I used n8n's Execute Sub-workflow in the parent and When Executed by Another Workflow in the child to modularize the audit log flow. I expected the parent to hand off the payload, wait for completion, and receive a clean child result back.
**What broke:** The parent often stayed running while the child showed no usable completion state or returned inconsistent output. The execution path became hard to reason about and hard to debug reliably.
**Root cause:** The most likely cause was instability in n8n's sub-workflow handoff/return path rather than in the audit logic itself. This is consistent with community reports about edge cases in sub-workflow execution and output propagation. I did not isolate a single definitive defect — keeping that honest matters more than a false root-cause attribution. In practice, the pattern introduced a vendor-specific control path that was harder to observe than a plain request/response boundary.
**Fix:** I replaced the sub-workflow coupling with a standard Webhook + HTTP Request pattern, so the audit logger became a separately callable workflow with an explicit request and response contract. This made the boundary testable and easier to debug step by step.
**Generalizes to:** When the trade-off is otherwise equal, prefer a widely understood protocol boundary over a platform-specific orchestration primitive because it improves observability, portability, and debugging.

---

## 2026-05-28T11:08 — Validator Schema Drift

**Phase:** Debugging
**What I tried:** I tested the webhook with a cURL payload that included ticket data. I expected the runtime validation behavior to match what the schema file declared.
**What broke:** The webhook input looked valid from one layer's perspective and invalid from another. The schema referenced `body`, while the validation logic was checking `payload.message`. That produced confusing output and false-negative validation behavior.
**Root cause:** The schema definition and the runtime validator drifted apart, so the declared contract and the executed contract were no longer the same. n8n webhook handling is sensitive to where the payload actually lives, such as `$json.body`, so validating against the wrong path creates exactly this kind of mismatch.
**Fix:** I aligned the validator JavaScript code with the schema file. Specifically, I replaced `payload.message` references with `payload.body` and added enum and required-field checks for `customer_type`, `channel`, and `customer_id` that the schema declared but the validator did not enforce.
**Generalizes to:** A schema only helps if runtime validation reads from the exact same source of truth; otherwise the contract exists in documentation but not in execution.

---

## 2026-05-28T11:08 — Pipeline Data Path Bug

**Phase:** Debugging
**What I tried:** I expected fields like `ticket_id` to remain available after downstream service nodes, and I referenced them again later in Edit Fields1. I ran the pipeline through the audit HTTP request and sheet append steps assuming the original item data would still be intact.
**What broke:** `ticket_id` came back as `null` in Edit Fields1 even though it existed earlier in the flow. The service nodes returned their own payloads, which displaced the item shape I was still trying to reference downstream.
**Root cause:** The pipeline treated service-node responses as if they were passive pass-through steps, but nodes like HTTP Request and Sheet append can replace or reshape the active item with their own response data. Community guidance around combining prior data with HTTP results points to this exact failure mode when earlier context is not preserved explicitly.
**Fix:** In Edit Fields1 (which runs after the HTTP and Sheet nodes), I replaced direct references like `{{ $json.ticket_id }}` with source-node references like `{{ $('Normalize Final Record').item.json.ticket_id }}`. This bypasses the service-node-overwritten item and reads directly from the source node's output by name.
**Generalizes to:** In workflow systems, service nodes are not neutral transport layers; if a field matters later, preserve it explicitly or reference it from the source node by name before any node that can replace the active item.

## 2026-05-30THH:MM — Iterated Before Establishing Measurement Resolution

**Phase:** Evaluation methodology
**What I tried:** I iterated the scoring prompt v1→v2 (added Authority Hierarchy, few-shot, sharpened definitions) and measured the result as +3.3pp (76.7% → 80.0%) on a single run over 30 tickets.
**What broke:** I declared v2 an improvement before knowing whether my measurement could even resolve a difference that small. At n=30, one ticket equals 3.3pp — the entire claimed improvement was a single ticket, well within the noise floor of a non-byte-deterministic model at temperature 0.
**Root cause:** I optimized before establishing measurement resolution. I treated a single run as ground truth when LLM outputs vary run-to-run even at T=0 (TH-04535 demonstrated this directly).
**Fix:** Multi-run eval (5 runs per version) to quantify variance, and honest reframing of n=30 as a coverage eval, not a production-grade comparison. Test-set expansion to n≥100 deferred to a later iteration / Build 2 foundation.
**Generalizes to:** Establish measurement resolution before iterating. If one test item moves the metric more than the improvement you're claiming, your eval cannot resolve the change — measurement design must precede optimization, not follow it.

## 2026-05-31THH:MM — n=1 Eval Masked Both the True Baseline and the Real Effect Size

**Phase:** Evaluation methodology
**What I tried:** Originally compared scoring prompt v1 (76.7%) vs v2 (80.0%) on a single run over 30 tickets, concluding a +3.3pp improvement.
**What broke:** The single-run comparison was misleading in two directions at once. A 5-run multi-eval showed v1's true mean was 64.0% (±2.8%), not 76.7% — the original v1 figure was an optimistic outlier. And v2's real advantage was +14pp (78.0% ±3.8%), not +3.3pp — far larger than a single run suggested. Non-overlapping ranges confirm the improvement is real, not noise.
**Root cause:** A single run of a non-byte-deterministic model (temperature 0 does not guarantee reproducibility) can land anywhere in the model's output distribution. The original v1 run happened to land high; the v1-vs-v2 gap happened to look small. Neither was representative.
**Fix:** 5 runs per version, mean ± standard deviation, overlap check. Reframed v1/v2 reporting around distributions, not point estimates.
**Generalizes to:** A single eval run is not a point on a line — it is one sample from a distribution. It can mislead in either direction: inflating a weak baseline or hiding a real effect. Report mean ± stddev over multiple runs, and check whether ranges overlap before claiming (or dismissing) a difference.

---

# Audit deferrals — consciously NOT fixed in v2.1

A spec-vs-implementation audit (2026-06-12) found a set of gaps between what the docs promise and what the workflow does. The four highest-leverage items were fixed in this pass (docs reconciliation, webhook header-auth, a minimal safety-critical routing rule, and the failure-log honesty below). The entries here record the gaps we are *deliberately* carrying into v3 rather than fixing now — each with what the audit found, why it's deferred, and what v3 should do. Logged so the deferral is a decision, not an oversight.

## 2026-06-12 — Audit deferral: audit-log workflow persists nothing

**Phase:** AUDIT (deferral)
**What the audit found:** The main workflow POSTs each scored ticket to a separate "Audit Log" webhook, but that workflow only reshapes the payload and responds `{ok:true}` — it writes to no datastore. "Structured logs for each run" is, in practice, a no-op echo, and it only fires on the success path (rejected/extraction-failed runs log nothing).
**Why deferred:** Durable audit persistence needs a real datastore and a retention policy (proposed 30 days, longer only anonymized), which is the same v3 work as moving off Google Sheets. Standing up a throwaway store now would be rework. n8n execution metadata (`customData`) gives a thin per-run trail in the meantime.
**v3 fix:** Persist audit events to the v3 datastore (Postgres), on every path including rejection and failure, with bounded retention and access control. Make the audit write a first-class step, not a fire-and-forget HTTP call.

---

## 2026-06-12 — Audit deferral: extractor output discarded, output contract incomplete

**Phase:** AUDIT (deferral)
**What the audit found:** The extractor's structured facts (`intent`, `entities`, `summary_de/en`) are validated and then dropped — the tier-multiplier code node reads only the scoring output and the raw webhook, never merging extraction facts forward. As a result the final record omits SCOPE's required `intent`, `extracted_facts`, `reason_summary`, `prompt_version`, and `model_version`; only `severity_reasoning` and a hardcoded `workflow_version` survive.
**Why deferred:** Carrying these fields through is cheap, but they only earn their keep once there's a storage and explainability surface that consumes them (the v3 datastore and review UI). Emitting them into a Google Sheet now would widen the contract without a consumer.
**v3 fix:** Merge the validated extraction object into the final record, emit the full output contract, and capture `prompt_version` + `model_version` (pin a dated model alias) at the point of each LLM call.

---

## 2026-06-12 — Audit deferral: seasonality applied twice [RESOLVED]

**Phase:** AUDIT (deferral)
**What the audit found:** Season influences priority in two places at once — the scoring prompt instructs the LLM to reduce severity for out-of-season heating-only failures, and the tier-multiplier code then multiplies by a 0.7 out-of-season factor. ADR-003's rationale ("time-based deterministic rules in code, context-dependent heuristics in the LLM") says season should live only in code.
**Why deferred:** Untangling this means re-tuning the scoring prompt and re-running the multi-run eval to confirm accuracy doesn't regress — more than a minimal-diff change, and exactly the kind of prompt iteration the eval discipline says not to do against a 30-ticket set without measurement headroom.
**v3 fix:** Remove the seasonal-reduction instruction from the scoring prompt so severity reflects objective state only, leave the deterministic season factor solely in code, and re-baseline accuracy on the expanded (n≥100) test set.
**Resolved (2026-06-12):** Removed the seasonal-reduction instruction from scoring_v2.txt; season is now applied once, deterministically, in the tier-multiplier code node. Pending re-baseline on the next multi-run eval.

---

## 2026-06-12 — Audit deferral: scoring output not schema-validated downstream

**Phase:** AUDIT (deferral)
**What the audit found:** Extraction output passes through a dedicated validator + IF gate, but scoring output flows straight into the tier-multiplier code node with no schema validation node. The asymmetry is a gap against "All outputs conform to the output schema."
**Why deferred:** The risk is largely covered today: the scoring LLM runs in strict `json_schema` mode and the code node fail-fasts (`throw`) on an unknown severity value. The missing piece is a routed failure path, which is entangled with the extraction-failure-routing item below — best fixed together.
**v3 fix:** Add a scoring-output validation node mirroring the extraction validator, and route its failures to the same human-review queue rather than an unhandled throw.

---

## 2026-06-12 — Audit deferral: extraction-failure path rejects instead of queuing for review

**Phase:** AUDIT (deferral)
**What the audit found:** When extraction validation fails, the workflow returns HTTP 422 and stops. SCOPE's mandatory-review rules say a validation failure with partial data still visible should route to `human_review_mandatory`, not be dropped — the partial extraction is discarded and nothing reaches a human.
**Why deferred:** This depends on the v3 human-review queue and durable storage existing; without a place to park partial results for a reviewer, "queue for review" has nowhere to go. v2.1 ships only the safety-critical routing rule.
**v3 fix:** On extraction or scoring validation failure, persist the partial record and route it to `human_review_mandatory` instead of returning a terminal 4xx.

---

## 2026-06-12 — Audit deferral: input validator narrower than webhook_input.schema.json

**Phase:** AUDIT (deferral)
**What the audit found:** The "Validate Webhook Input" code node checks required fields, three enums, and date-parseability, but ignores most of the declared schema: no `ticket_id` pattern/length, no `body` max-length, no `sender_email` format, no `building_type`/`occupant_flags` enums, and no `additionalProperties: false` — so unknown/garbage fields pass silently. It's a hand-rolled subset, not validation against the schema.
**Why deferred:** The current subset blocks the malformed payloads that actually break downstream logic (missing/invalid tier, type, date). The residual gaps are breadth, not a live failure. Replacing bespoke checks with a real JSON Schema validator (e.g. an Ajv-backed node) is a small but distinct piece of work better done once.
**v3 fix:** Validate the inbound payload against `webhook_input.schema.json` directly with a schema validator, including `additionalProperties: false`, instead of maintaining a parallel hand-coded subset that can drift (it already drifted once — see Validator Schema Drift, 2026-05-28).

---

## 2026-06-12 — Audit deferral: minor items (cosmetic / low-risk)

**Phase:** AUDIT (deferral)
**What the audit found:** Four low-severity items: (1) the inbound webhook path is `support-triage-v1` in the v2 workflow — stale naming; (2) the Google Sheets schema has a column id `"customer_tier "` with a trailing space — silent data-quality risk; (3) SCOPE's "Required inputs" names `created_at`/`message_body` while the schema and code use `received_at`/`body` — doc/impl naming drift; (4) `confidence` is produced (and the prompt even drops it below 0.3 on missing fields) but nothing downstream consumes it for routing.
**Why deferred:** None of these change a triage outcome today. Renaming the live webhook path breaks any caller already pointed at it; fixing the column id requires a coordinated sheet migration; the naming drift is harmless until the deferred fields above are emitted; and `confidence`-threshold routing is explicitly a v3 capability (the threshold is still an open question in SCOPE).
**v3 fix:** Rename the webhook path to a version-neutral route with a deprecation window for callers; correct the `customer_tier` column id during the v3 storage migration; reconcile `created_at`/`message_body` naming when the full output contract lands; and wire `confidence` into routing once it's calibrated and a threshold is agreed.
**Resolved (2026-06-12):** Item (2) fixed — removed the trailing space from the `customer_tier` sheet column id (and displayName) so it maps from the triage record. Items (1), (3), (4) remain deferred.

---

## 2026-06-12 — Sheet field-name bug: Normalize `=confidence` assignment [RESOLVED]

**Resolved (2026-06-12):** Surfaced once the Sheets data-path fix let the triage record reach the append node — the Normalize Final Record assignment was named `=confidence` (stray `=` prefix), so the emitted key never matched the `confidence` column. Renamed the assignment to `confidence`.

---

# Prompt-robustness review deferrals — 2026-06-12

A prompt-and-LLM-call review (2026-06-12) surfaced robustness gaps in the extraction/scoring prompts and their schemas. Three were fixed in the same pass (clean scoring-input assembly, seasonality de-dup, injection delimiter on the extractor). The entries below are the findings we are deliberately carrying forward — each with what the review found, why it's deferred, and what v3 should do.

## 2026-06-12 — Prompt review deferral: extraction schema carries no structured severity signals

**Phase:** PROMPT REVIEW (deferral)
**What the review found:** Every signal that flips severity — heating state (working/degraded/failed), safety signal (gas/smoke/burning/excess heat), vulnerable-occupant mention, affected-unit count, outdoor temperature, customer-stated urgency — has to survive lossy compression into two ≤200-char summaries, because the extraction schema has no structured fields for them. The "vulnerable occupants OVERRIDE" and "safety signals are ALWAYS critical" rules in the scoring prompt can only fire on facts that happen to land in a summary sentence.
**Why deferred:** Adding fields (`heating_state`, `safety_signal`, `vulnerable_occupants`, `affected_unit_count`, `outdoor_temp_c`, `customer_stated_urgency`) changes the extraction contract and forces a re-baseline of the eval, plus rework of the scoring prompt to consume them. That is a deliberate schema iteration, not a minimal diff — out of scope for this pass (which only cleaned up the input *plumbing*, not the schema). The scoring-input assembly node added in this pass mitigates the worst of it by forwarding the original `ticket_excerpt` and the structured webhook fields (`occupant_flags`, `customer_type`, etc.) to the scorer.
**v3 fix:** Extend the extraction schema with explicit structured severity signals so the authority-hierarchy and override rules become near-mechanical rather than dependent on summary prose, and have scoring consume the structured signals directly.

---

## 2026-06-12 — Prompt review deferral: summary over-length 422s the whole ticket; no scoring-output validator

**Phase:** PROMPT REVIEW (deferral)
**What the review found:** OpenAI strict structured outputs does not constrain `maxLength` (it ignores string-length, numeric-range, `pattern`, and `format`), so the 200-char summary cap is enforced only post-hoc by the extraction validator — which then rejects the *entire* ticket (HTTP 422) for a 201-char summary. Symmetrically, scoring output has no validator node at all, so `severity_reasoning` length and `confidence` range are checked nowhere.
**Why deferred:** Both touch the failure-routing design: a too-long summary should degrade gracefully (truncate / soft-warn) rather than reject, and a scoring validator only earns its keep once its failures route somewhere (the v3 human-review queue) instead of throwing. Wiring graceful degradation and a scoring validator into the success/failure branches is more than a minimal diff and overlaps the deferred extraction-failure-routing work.
**v3 fix:** Make the summary length a soft constraint (truncate to 200 and flag, don't 422), and add a scoring-output validation node mirroring the extraction validator, routing its failures to human review rather than an unhandled throw.

---

## 2026-06-12 — Prompt review deferral: `language` enum cannot emit "unknown"

**Phase:** PROMPT REVIEW (deferral)
**What the review found:** The extraction prompt instructs the model to use `"unknown"` for empty/unintelligible tickets, but the extraction schema's `language` enum is `["de","en","other"]` — strict decoding forbids `"unknown"`, so the instruction is dead. The webhook input schema's `language` enum *does* include `unknown`, so the two layers disagree.
**Why deferred:** It is a one-line enum change, but it alters the extraction output contract and should land together with the other schema work (structured severity signals above) and a re-baseline, rather than as an isolated tweak that shifts outputs mid-eval.
**v3 fix:** Add `"unknown"` to the extraction `language` enum (aligning it with the webhook schema), or change the empty-ticket instruction to use `"other"`. Pick one and make the prompt and schema agree.

---

## 2026-06-12 — Prompt review deferral: per-intent few-shot examples promised but still absent

**Phase:** PROMPT REVIEW (deferral)
**What the review found:** The 2026-05-04 BUILD entry ("Extraction misclassified appointment scheduling as 'other'") logged the fix as "Defer to v2. Add few-shot examples to system prompt, one canonical example per intent." The extraction prompt is byte-identical across v1 and v2 (prompts/README confirms it) — the promised per-intent examples were never added, so intent still collapses to `other` under ambiguity.
**Why deferred:** Intent accuracy is not measured by the severity eval, so adding examples now would change the extraction prompt without a metric to confirm the gain or guard against regression. It belongs with a dedicated intent-classification eval, which does not exist yet.
**v3 fix:** Add one canonical few-shot example per intent enum value to the extraction prompt, and stand up an intent-accuracy eval so the change is measurable rather than asserted.

---

## 2026-06-12 — Prompt review deferral: `confidence` is computed but never consumed

**Phase:** PROMPT REVIEW (deferral)
**What the review found:** The scoring prompt elaborately defines `confidence` (drop below 0.3 on missing key fields, below 0.5 when ambiguous) and the schema carries it, but nothing downstream reads it — no node routes on it, and the safety-critical routing rule ignores it. The signal the prompt works to produce is inert. (Also tracked in the audit minor-items entry; restated here from the prompt's perspective.)
**Why deferred:** Confidence-threshold routing is an explicit v3 capability and the threshold is still an open question in SCOPE; the prompt's confidence values are also not calibrated, so wiring them into routing now would route on an unvalidated number.
**v3 fix:** Calibrate confidence against ground truth, agree a threshold, then route low-confidence tickets to mandatory human review — or, if it stays uncalibrated, stop claiming it gates review.

---

## 2026-06-12 — Prompt review deferral: undated `gpt-4.1-mini` model alias

**Phase:** PROMPT REVIEW (deferral)
**What the review found:** Both LLM nodes pin the model as the undated alias `gpt-4.1-mini`. A silent provider-side update to the alias can shift behavior under a frozen prompt, which directly undermines prompt-robustness work and eval reproducibility (the README already notes the v1 76.7%→64.0% level shift may partly reflect this).
**Why deferred:** Pinning a dated snapshot is a config change best made alongside the eval-set expansion (n≥100) so the new baseline is measured against a fixed model, not changed piecemeal between runs.
**v3 fix:** Pin a dated model version (`gpt-4.1-mini-YYYY-MM-DD`) in both LLM nodes and record `model_version` in the output contract so every run is attributable to a specific model snapshot.