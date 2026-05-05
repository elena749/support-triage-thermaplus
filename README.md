# Support Triage System — ThermaPlus GmbH (Reference Build)

**Loom demo:** *[link goes here after recording]*

---

## What it does / Was es macht

**EN:** A support triage system that classifies and prioritizes incoming support tickets, so support teams act on the right ticket first. Built on n8n with two specialized LLMs (extraction + severity scoring) and a deterministic tier multiplier.

**DE:** Ein Support-Triage-System, das eingehende Tickets klassifiziert und priorisiert, damit Support-Teams das richtige Ticket zuerst bearbeiten. Gebaut auf n8n, mit zwei spezialisierten LLMs (Extraktion + Severity-Scoring) und einem deterministischen Tier-Multiplier.

*Reference customer: ThermaPlus GmbH (fictional). Heizung & Wärmepumpe service across Bayern and Baden-Württemberg, ~80 employees, B2C and B2B Hausverwaltungen.*

---

## Why a customer would care

In 2026, customer expectations of support response times have shifted. AI has trained users to expect immediate, accurate answers, and a 24-hour first-response window now reads as broken. Mittelstand support teams have not scaled headcount to match.

For a heating service like ThermaPlus, the cost of bad triage is concrete: a frozen family waits behind a billing query because tickets are worked in arrival order. This system classifies and prioritizes every incoming ticket before a human looks at it, so the team works the right one first.

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
severity + confidence
↓
Tier multiplier (deterministic)
↓
final priority = severity × tier × season
↓
Google Sheet (v1 storage) → human review

**Why two LLMs.** Extraction is fact-pulling, scoring is judgment. Mixing them in one prompt forces the model to trade attention; separating them improves accuracy on both and makes failures debuggable. *Separation of concerns / Trennung von Zuständigkeiten.*

**Tier multiplier as deterministic logic.** Customer tier (A/B/C) and season (in/out of heating season) are static metadata. Putting their math in code, not an LLM, makes the priority auditable and explainable to a DPO. The answer to "why was my ticket prioritized this way?" is `severity × tier × season`, not "the model thought so."

**Domain knowledge lives in two places.** The scoring prompt encodes German heating-specific rules: heating-season corridor (Oct 1 to Apr 30 per case law), outdoor-temperature thresholds, vulnerable-occupant overrides, safety-signal overrides. The tier-multiplier code encodes the deterministic season factor. Context-dependent heuristics in the LLM, time-based deterministic rules in code.

**Storage.** Google Sheet for v1 (inspectable by eye, easy to grade). Postgres or a real database becomes appropriate at v3+.

---

## Eval Results

### v1 baseline (5 May 2026)

Held-out test set: 30 synthetic ThermaPlus tickets with ground-truth annotation. Tickets deliberately cover the edge cases that hurt: vulnerable households, calmly-critical phrasings, multi-property B2B, mixed language, panic-but-cosmetic.

**Severity Accuracy: 76.7% (23/30)**

|              | low | medium | high | critical |
|--------------|-----|--------|------|----------|
| **low**      | 8   | 1      | 0    | 0        |
| **medium**   | 4   | 4      | 0    | 0        |
| **high**     | 0   | 2      | 7    | 0        |
| **critical** | 0   | 0      | 0    | 4        |

Critical: 4 of 4 correct, no false negatives on safety-relevant tickets. All 7 failures are off by exactly one level, indicating solid domain understanding but miscalibrated thresholds. Three failure patterns: (1) pipeline overweights customer self-assessment in both directions, (2) routine inquiries with business relevance or frustration get rated low instead of medium, (3) early-warning signals get rated medium instead of high.

### v2 after prompt iteration (5 May 2026)

Same test set. Prompt changes: added an Authority Hierarchy section (objective state outranks customer framing), sharpened the low/medium boundary to cover routine-with-escalation-risk, added three in-prompt few-shot examples derived from v1 failures.

**Severity Accuracy: 80.0% (24/30), up from 76.7% in v1.**

|              | low | medium | high | critical |
|--------------|-----|--------|------|----------|
| **low**      | 8   | 1      | 0    | 0        |
| **medium**   | 3   | 5      | 0    | 0        |
| **high**     | 0   | 2      | 7    | 0        |
| **critical** | 0   | 0      | 0    | 4        |

**Honest reading.** v2 fixed exactly one of seven v1 failures (TH-04559, angry customer with no functional emergency). The other six persist with reasoning patterns close to v1. For at least one of these (TH-04535), an isolated single-ticket test produced the correct `high` answer while the same prompt in batch produced `medium`. Same prompt, same temperature=0, different output: a reminder that LLM outputs are not byte-deterministic at T=0, and that prompt-level mitigations have diminishing returns where the model holds a strong learned prior. n=1 evaluation cannot distinguish weak mitigation from inherent variance. Credible before/after needs multi-run eval (mean ± stddev), not point estimates.

---

## Cost & Latency

End-to-end latency, measured client-side via curl timestamps:

| Version | n  | min     | p50     | p95      | max      |
|---------|----|---------|---------|----------|----------|
| v1      | 30 | 5,499ms | 8,329ms | 12,002ms | 12,863ms |
| v2      | 29 | 6,002ms | 8,427ms | 13,119ms | 16,494ms |

Median is essentially unchanged from v1 to v2 (+1%). p95 grew ~9%, max ~28%. The longer v2 prompt adds tokens to every call but the median impact is small; the wider tail comes from OpenAI server-side variance plus one ticket where the Sheets append node hit a Google rate limit and retried (see FAILURE_LOG, 5 May 2026). Latency is dominated by the two sequential LLM calls and cannot be parallelized: scoring needs the extractor's output as input.

**Cost.** v1 logs no per-call cost. Estimated cost at this architecture (two gpt-4.1-mini calls, no RAG, no tools) is ~$0.001 per ticket. At ThermaPlus volume (≤500 tickets/month), under $1/month. Per-call cost telemetry was deliberately deferred to a build with architectures where forecasting matters (RAG, multi-step agents). Latency was instrumented because the cost is zero (timestamps around the curl call) and it produces the number an end-user feels.

---

## Security & Governance

Tickets contain PII: names, emails, phone numbers, addresses, sometimes payment details. Two customer types in scope: B2C private individuals (full DSGVO/GDPR), and B2B Hausverwaltungen (B2B contractual data, but DSGVO still applies to any tenant data inside).

**Data flow.** Tickets enter via authenticated webhook to n8n, get sent to the LLM provider (region and DPA terms depend on provider choice), and get stored in Google Sheets for v1. Production deployment requires EU-hosted storage and a signed DPA with the LLM provider. Logs containing ticket content must be access-controlled with bounded retention (proposed: 30 days, longer only with anonymization).

**What a DPO would flag in v1:** full ticket content in logs, US-region LLM processing without explicit DPA, indefinite retention. All addressed in the roadmap.

**Synthetic data only.** No real PII has been processed by this system.

---

## Roadmap

This is a v1+v2 demonstrator built over three days. The honest gap to production:

**Evaluation rigor.** Multi-run eval with variance bounds (mean ± stddev over 3-5 runs per version). Test set from 30 to 100+ tickets to make subgroup statistics meaningful.

**Mitigations for v3.** Two-stage verification (a second LLM pass critiques the first against the rules) for failure patterns where prompt-only does not stick. Dynamic few-shot retrieval (top 1-2 examples per ticket, not three static ones). Confidence-threshold routing once confidence values are calibrated.

**Architecture & ops.** Webhook auth, retry on every external API call, monitoring (latency, error rate, severity distribution, drift), staging environment with rollback.

**Compliance.** DPA with OpenAI and Google, audit trail, deletion policy, full GDPR review for real PII.

**Future builds, not v3 of this one.** RAG over resolved-ticket history. Suggested draft replies (the path to an agentic build). Real helpdesk connector (Freshdesk, Zendesk).

**Effort estimate.** MVP-production for one supervised customer: ~2-3 weeks. Multi-tenant production with SLA: 2-3 months. Enterprise with certification: 6-12 months and a small team.

---

## About this build

I built this to take a pattern from a personal project (separating extraction and scoring into two LLMs) and ask what it would look like for a real business with real volume and real governance constraints. ThermaPlus is fictional, shaped after Mittelstand companies drowning in support tickets. The discipline applied here, schema enforcement, eval, governance notes, prompt iteration with honest measurement, is what I would bring to a customer engagement.
