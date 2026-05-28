# SCOPE.md

# Support Triage System — v2 Scope
Status: v2 scope accepted; v2.1 implementation partial. See DECISIONS.md ADR-004 and ADR-005 for items planned but not yet built.
Version: v2-scope (drafted before v2.1; v2.1 covers a subset)
Date: 2026-05-28

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

- - Accept a structured inbound ticket via authenticated webhook. *[planned, not in v2.1]*
- Validate the inbound payload against a defined input schema.
- Extract structured facts from ticket text using an LLM.
- Score ticket severity using a separate LLM.
- Apply deterministic business logic for customer tier and seasonality.
- Produce a final priority and routing state.
- Store triage results for human review.
- Record structured logs for each run.
- - Route selected cases to mandatory human review. *[planned, not in v2.1]*

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

The system must produce:

- `ticket_id`
- `intent`
- `extracted_facts`
- `severity`
- `confidence`
- `tier_weight`
- `season_multiplier`
- `final_priority`
- `routing_state`
- `reason_summary`
- `workflow_version`
- `prompt_version`
- `model_version`
- `processed_at`

## Routing states

Allowed routing states in v2:

- `human_review_standard`
- `human_review_priority`
- `human_review_mandatory`
- `rejected_input`
- `processing_failed`

No v2 routing state implies autonomous downstream action.

## Mandatory human review cases

The system must route to `human_review_mandatory` when any of the following applies:

- Severity is `critical`.
- Confidence is below the agreed threshold.
- Key fields are missing or contradictory.
- Prompt-injection or instruction-like content is detected.
- Safety signals conflict with customer self-assessment.
- Duplicate or ambiguous property context exists.
- Extraction or scoring validation fails but partial data remains visible.
- A retry/recovery path was used after processing failure.

## Success criteria

v2 is successful if:

- Every inbound payload is either accepted or explicitly rejected.
- No malformed payload reaches the scoring stage.
- All outputs conform to the output schema.
- Every run records version metadata and processing outcome.
- Human-review rules are applied consistently.
- Evaluation is repeatable across multiple runs, not just one batch.
- The system can explain, at a high level, why a ticket was prioritized.

## Non-functional goals

For v2, target:

- Functional correctness above v1 baseline on held-out evaluation.
- Stable schema-valid output.
- Basic request authentication.
- Structured logging.
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