# DECISIONS.md

# Architecture Decisions — Support Triage System

## ADR-001: System is assistive, not autonomous
Status: Accepted
Date: 2026-05-28

### Decision
The system will recommend priority for human review and will not autonomously take irreversible actions.

### Why
This keeps the system aligned with a lower-risk support-assistive workflow, improves trust, and reduces operational/compliance risk.

### Consequences
- Human review remains part of the workflow.
- Output must include routing state, not just score.
- Future auto-action features require a new decision record.

---

## ADR-002: Extraction and scoring remain separate
Status: Accepted
Date: 2026-05-28

### Decision
Use one LLM step for fact extraction and a separate LLM step for severity scoring.

### Why
Extraction and judgment are distinct tasks. Separation improves debuggability and makes failures easier to isolate.

### Consequences
- Slightly higher latency.
- Clearer failure localization.
- Easier evaluation per stage.

---

## ADR-003: Deterministic business multipliers stay in code
Status: Implemented (v2.1)
Date: 2026-05-28

### Decision
Customer tier and seasonality logic remain deterministic code, not model judgment.

### Why
Static business rules should be auditable, explainable, and easy to test.

### Consequences
- Business logic can be unit-tested separately.
- Priority explanation becomes clearer.
- Model scope stays narrower.

---

## ADR-004: v2 uses mandatory human review states
Status: Implemented in v2.1 in minimal binary form (safety-critical → human_review_mandatory, else auto_accepted); graded review tiers deferred to v3
Date: 2026-05-28

### Decision
v2 will explicitly classify some tickets into mandatory review states instead of forcing every ticket through the same path.

### Why
The system is not reliable enough to treat all cases as equally safe. Edge cases and low-confidence cases need visible escalation.

### Consequences
- Review workload must be designed deliberately.
- Confidence and contradiction rules become first-class logic.
- Evaluation should include review-routing quality, not just severity accuracy.

---

## ADR-005: v2 requires authenticated input and structured logs
Status: Accepted
Date: 2026-05-28

### Decision
Webhook authentication and structured run logs are minimum v2 requirements.

### Why
Even a portfolio-grade enterprise prototype should not expose a public unauthenticated input path or run without traceability.

### Consequences
- Slightly more implementation effort in v2.
- Stronger security and explainability story.
- Easier transition to light v3.

---

## ADR-006: Google Sheets is allowed only as transitional v2 storage
Status: Accepted
Date: 2026-05-28

### Decision
Google Sheets may remain in v2 only as a temporary review surface, not as the intended long-term primary datastore.

### Why
Sheets is inspectable and useful for rapid evaluation, but weak as a production system of record.

### Consequences
- Migration to Postgres is expected in light v3.
- v2 documentation must frame Sheets as temporary.
- Review workflows should avoid depending on Sheets-specific behavior.