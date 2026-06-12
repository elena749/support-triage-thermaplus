# SCOPE.md

# Support Triage System — v2 Scope
Status: v2 scope accepted; v2.1 implementation partial. See DECISIONS.md ADR-004 and ADR-005 for items planned but not yet built.
Version: v2-scope (drafted before v2.1; v2.1 covers a subset)
Date: 2026-05-28

Reconciliation note (2026-06-12): this document was drafted as full v2 scope. Several items it lists as required are deferred to v3 per ADR-003/ADR-004 — in particular the full routing-state machine, the full set of mandatory-review triggers, structured audit persistence, and the full output contract. Those items are tagged inline below as v3 scope. v2.1 implements a reduced subset (authenticated webhook, input validation, two-LLM pipeline, deterministic priority, and a single safety-critical routing rule). See README.md → "What v2.1 implements vs. what is deferred to v3".

## Purpose

This system assists a support team by classifying and prioritizing incoming support tickets before human review.

It is designed for a heating-service support workflow where response order matters and where objective urgency signals may be buried in natural-language ticket text.

The system is assistive, not autonomous. It recommends a severity and final priority for human review; it does not make irreversible operational decisions.

## Intended use

The system receives an inbound ticket payload, extracts relevant facts, assigns a severity score, applies deterministic business multipliers, and writes the result to a review queue for human action.

Primary user:
- Internal support or dispatch-adjacent staff reviewing ticket priority.

Primary outcome:
- Help staff work the right ticket first.

## In scope

The v2 system will:

- Accept a structured inbound ticket via authenticated webhook. *[implemented in v2.1: n8n header-auth credential]*
- Validate the inbound payload against a defined input schema. *[v2.1: partial — validator enforces a subset of webhook_input.schema.json; full schema enforcement is v3]*
- Extract structured facts from ticket text using an LLM.
- Score ticket severity using a separate LLM.
- Apply deterministic business logic for customer tier and seasonality.
- Produce a final priority and routing state. *[v2.1: final priority + minimal routing_state (human_review_mandatory / auto_accepted); full routing state is v3, ADR-004]*
- Store triage results for human review.
- Record structured logs for each run. *[v2.1: partial — per-run metadata in n8n execution data; durable audit persistence is v3, ADR-005 follow-on]*
- Route selected cases to mandatory human review. *[v2.1: safety-critical only (critical severity / safety signal); full mandatory-review trigger set is v3, ADR-004]*

## Out of scope

The v2 system will not:

- Auto-close tickets.
- Auto-dispatch technicians.
- Trigger customer communications automatically.
- Decide warranty, refund, or entitlement outcomes.
- Make legal, financial, employment, or identity-related decisions.
- Learn online from user actions without explicit review and redeployment.
- Operate as a customer-facing chatbot.
- Process attachments, images, or voice inputs.
- Support multi-tenant production deployment.
- Serve as the final system of record for enterprise production.

## Intended system boundary

Input boundary:
- Authenticated webhook receives structured ticket payload.

Processing boundary:
- Validation, extraction, scoring, deterministic priority calculation.

Output boundary:
- Human review queue plus structured logs.

Human boundary:
- A human remains responsible for final operational action.

## Risk posture

Current intended use is support-assistive triage, not autonomous decision-making.

The system should be treated as:
- Assistive workflow software with AI components.
- Human-in-the-loop by default.
- Not approved for high-stakes automated decisions.

If future scope expands into entitlement, employment, credit, identity, law enforcement, or other regulated decisioning, the classification and controls must be reassessed before deployment [web:10][web:251].

## Required inputs

Minimum required fields for v2:

- `ticket_id`
- `created_at`
- `customer_type`
- `customer_tier`
- `language` or detectable message text
- `subject`
- `message_body`

Optional but supported:

- `customer_name`
- `email`
- `phone`
- `address`
- `property_count`
- `prior_ticket_count`
- `channel`
- `building_type`
- `occupant_flags`

## Output contract

The full v2 output contract is below. v2.1 emits a subset; fields not yet emitted are tagged *[v3]* and are deferred per ADR-004 (the extractor's facts are not yet merged into the final record).

- `ticket_id`
- `intent` *[v3]*
- `extracted_facts` *[v3]*
- `severity`
- `confidence`
- `tier_weight`
- `season_multiplier`
- `final_priority`
- `routing_state` *[v2.1: minimal — human_review_mandatory / auto_accepted; full state set is v3]*
- `reason_summary` *[v3; v2.1 emits `severity_reasoning` only]*
- `workflow_version`
- `prompt_version` *[v3]*
- `model_version` *[v3]*
- `processed_at`

## Routing states

Allowed routing states in v2 (full set, v3 target):

- `human_review_standard` *[v3]*
- `human_review_priority` *[v3]*
- `human_review_mandatory` *[v2.1]*
- `rejected_input` *[v3 as an emitted routing_state; v2.1 returns HTTP 4xx on invalid input]*
- `processing_failed` *[v3]*

v2.1 emits a reduced two-value set: `human_review_mandatory` (safety-critical) and `auto_accepted` (everything else). `auto_accepted` is a v2.1-only transitional value; v3 replaces it with the graded human-review tiers above.

No routing state implies autonomous downstream action.

## Mandatory human review cases

The system must route to `human_review_mandatory` when any of the following applies. v2.1 enforces only the first trigger (in code); the remaining triggers are v3 (ADR-004), since they depend on calibrated confidence and contradiction detection that do not exist yet.

- Severity is `critical`, or a gas/safety signal is present. *[v2.1: enforced deterministically in the tier-multiplier code node]*
- Confidence is below the agreed threshold. *[v3]*
- Key fields are missing or contradictory. *[v3]*
- Prompt-injection or instruction-like content is detected. *[v3]*
- Safety signals conflict with customer self-assessment. *[v3]*
- Duplicate or ambiguous property context exists. *[v3]*
- Extraction or scoring validation fails but partial data remains visible. *[v3]*
- A retry/recovery path was used after processing failure. *[v3]*

## Success criteria

v2 is successful if:

- Every inbound payload is either accepted or explicitly rejected.
- No malformed payload reaches the scoring stage.
- All outputs conform to the output schema. *[v2.1: scoring output is not yet schema-validated downstream; v3]*
- Every run records version metadata and processing outcome. *[v2.1: partial — success-path metadata in n8n execution data; durable per-run audit persistence is v3]*
- Human-review rules are applied consistently. *[v2.1: the single safety-critical rule; full rule set is v3]*
- Evaluation is repeatable across multiple runs, not just one batch.
- The system can explain, at a high level, why a ticket was prioritized.

## Non-functional goals

For v2, target:

- Functional correctness above v1 baseline on held-out evaluation.
- Stable schema-valid output.
- Basic request authentication. *[v2.1: implemented — header-auth credential]*
- Structured logging. *[v2.1: partial — n8n execution metadata; durable audit persistence is v3]*
- Clear deferral behavior.
- Inspectable and explainable deterministic priority logic.

## Explicit non-goals for v2

These are intentionally deferred to light v3 or later:

- Postgres as primary storage.
- Idempotency and duplicate suppression.
- Retry classification by failure type.
- Dead-letter queue.
- Rich monitoring dashboards.
- Full privacy redaction layer.
- Full audit trail for enterprise production.
- Formal DPIA package.

## Assumptions

- Test data is synthetic.
- Human reviewers are available.
- Ticket volume is low enough that batch-scale saturation is not the primary design constraint in v2.
- The workflow is being developed as a portfolio-grade, enterprise-shaped prototype rather than a live certified product.

## Open questions

- Exact confidence threshold for mandatory human review.
- Whether prompt-injection detection is rule-based, model-based, or hybrid in v2.
- Whether duplicate handling belongs in late v2 or only light v3.
- Whether seasonality stays deterministic only or gains region-aware overrides later.