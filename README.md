# Support Triage System — ThermaPlus GmbH (Reference Build)

**Loom demo:** *[link goes here after recording]*

---

## What it does / Was es macht

**EN:** A support triage system that classifies and prioritizes incoming support tickets so support teams act on the right ticket first — keeping their customers happy and reducing customer churn.

**DE:** Ein Support-Triage-System, das eingehende Support-Tickets klassifiziert und priorisiert, damit Support-Teams das richtige Ticket zuerst bearbeiten — zufriedene Kunden, weniger Churn.

*Reference customer: ThermaPlus GmbH (fictional) — Heizung & Wärmepumpe service across Bayern and Baden-Württemberg, ~80 employees, serving B2C homeowners and B2B Hausverwaltungen.*

---

## Why a customer would care

ThermaPlus GmbH (fictional reference customer): heating and Wärmepumpe service across Bayern and Baden-Württemberg, ~80 employees, serving B2C homeowners and B2B Hausverwaltungen. The support inbox mixes urgent breakdowns ("Heizung aus, -2°C, zwei Kinder zuhause") with routine maintenance scheduling and invoice questions. Without triage, the team works tickets in arrival order — and a frozen family waits behind a billing query.

In 2026, customer expectations of response time have shifted. AI has trained users to expect immediate, accurate answers. A 24-hour first-response window that felt normal three years ago now reads as broken. Mittelstand support teams haven't scaled headcount to match — the gap widens daily.

This system reduces that gap by classifying and prioritizing every incoming ticket before a human looks at it. The team works the right ticket first, every time.

---

## Architecture

Webhook trigger (incoming ticket)
      ↓
[ Extraction LLM ]  → schema validation
      ↓
  structured ticket JSON
      ↓
[ Scoring LLM ]     → schema validation
      ↓
  severity score (1-5) + confidence
      ↓
Tier multiplier (deterministic business logic)
      ↓
Final priority = severity × tier weight
      ↓
JSON output → storage (Google Sheet for v1)
      ↓
Human reviews and acts

Every LLM call is logged: input, output, latency, tokens, cost.

### Walkthrough

**Trigger.** The helpdesk fires a webhook to our n8n endpoint whenever a new ticket arrives. The payload carries the ticket text plus metadata (sender, ticket ID, timestamp). No polling — events drive the flow.

**Why two LLMs, not one.** Extraction and scoring are different cognitive tasks. Extraction is fact-based: read the ticket, pull structured fields out of unstructured text. Scoring is judgment: take the structured fields and assign severity. Mixing them in one prompt forces the model to trade attention between two jobs, which lowers accuracy on both. Separating them also makes failures debuggable — when output is wrong, we know which stage to inspect. This is separation of concerns / Trennung von Zuständigkeiten.

**Tier multiplier as deterministic logic.** Customer tier (A/B/C, based on contract value or strategic weight) is static metadata. Multiplying severity by a tier weight is business logic, not a judgment call — putting it in code instead of an LLM makes the priority auditable and explainable to a DPO. A customer asking "why was my ticket prioritized this way?" gets a deterministic answer: severity × tier.

**Storage.** Google Sheet for v1. Every result writes one row. Inspectable by eye, easy to grade during the eval phase, no infrastructure to set up. Postgres or a real database becomes appropriate at v3+ when volume grows.

**Human in the loop.** v1: every ticket reviewed by a human before action. The system surfaces priority; humans decide. v2: confidence-gated automation — high-confidence, low-stakes tickets (e.g. routine maintenance scheduling) can route automatically; ambiguous or high-severity tickets always escalate to human review.

Build 1 incorporates German heating-domain knowledge in two places. (1) Scoring LLM prompt: heating-season corridor (Oct 1 – Apr 30 per case law), outdoor-temperature thresholds for heating necessity (11–17°C depending on building energy class), and vulnerable-occupant overrides. (2) Tier-multiplier code: deterministic season-multiplier (1.0 in season, 0.7 out of season). The split mirrors a core principle — context-dependent heuristics in the LLM, time-based deterministic rules in code.

---

## Cost, latency, governance

Cost & Latency Profile
v1 erfasst keine Per-Call-Kosten oder Latenz-Metriken. Bei der Zielarchitektur (zwei gpt-4.1-mini-Calls pro Ticket, kein RAG, keine Tool-Calls) liegen die geschätzten Kosten bei ~$0.001/Ticket. Bei einem realistischen Volumen für ThermaPlus (≤500 Tickets/Monat) ergibt das <$1/Monat — Telemetrie-Overhead in der Größenordnung des Messobjekts.
Das Pattern (Per-Call-Logging mit Token/Latency/Cost in separater Telemetry-Tabelle, fail-open angeschlossen) wird in Build [N] eingeführt, sobald RAG-Kontexte oder Multi-Step-Agents die Kosten in einen Bereich bringen, wo Forecasting business-relevant wird.
Was ich gemessen habe: End-to-End-Latency p50/p95 über 30 Test-Tickets (siehe Eval-Sektion).

**Cost.** LLM calls dominate. Webhook, schema validation, and tier multiplication add negligible cost. For v1 with two LLM calls per ticket, expected cost is single-digit cents per 100 tickets at current model pricing. Exact numbers measured after instrumentation and reported here.

**Latency.** Two LLM calls run sequentially. Expected p50 in the 3–5 second range, p95 in the 8–12 second range. Webhook delivery and schema validation are sub-100ms and not the bottleneck. Real numbers reported after instrumentation.

**Governance.** Support tickets contain PII: names, email addresses, phone numbers, postal addresses, sometimes payment details. The system processes data from two customer types: B2C private individuals (full DSGVO/GDPR scope, including right to erasure and data minimization) and B2B Hausverwaltungen (B2B contractual data, lighter consent requirements but still subject to DSGVO for any contained personal data of tenants).

Data flow: ticket text leaves the helpdesk only via authenticated webhook to the n8n instance. LLM calls send ticket content to the model provider; the choice of provider determines processing region (EU vs US) and DPA terms. Storage in Google Sheet for v1 is acceptable for a reference build; production deployment requires EU-hosted storage and a signed DPA with the LLM provider. Logs contain ticket content and must be access-controlled; retention bounded (proposed: 30 days for debug logs, longer only with anonymization).

What a DPO would object to in v1: full ticket content in logs, US-region LLM processing without explicit DPA, indefinite retention. Mitigations land in v2 and are documented in the failure log.

---

## Results & next steps

**v1 vs v2 evaluation.** Held-out test set of 25 tickets graded on severity accuracy. Results reported here after eval phase.

**What I'd improve next (v3 territory, not built).**

- Knowledge base lookup: retrieval over resolved ticket history so the system can surface "we've seen this before, here's what worked." This is a RAG subsystem (embeddings, vector store, retrieval evaluation), substantial enough to be its own build.
- Suggested draft replies: extending the system from triage to first-draft response. The natural evolution into an agentic build that watches, drafts, escalates, and learns from human edits.
- Real helpdesk connector: replacing the synthetic webhook with a Freshdesk or Zendesk integration.
- Multi-dimensional scoring: adding churn risk and sentiment-trend signals beyond severity.

---

## About this build

I built this because I wanted to take a pattern I'd already used in a personal project — separating extraction and scoring into two LLM calls — and ask what it would look like for a real business with real volume and real governance constraints. The fictional reference customer (ThermaPlus GmbH) is shaped after Mittelstand companies drowning in support tickets. The discipline applied here — schema enforcement, instrumentation, structured eval, governance notes — is what I'd bring to a customer engagement.
