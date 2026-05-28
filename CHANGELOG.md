# Changelog

All notable changes to this build are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com).

---

## [v2.0-prompts-and-resilience] — 2026-05-05

### Changed
- Scoring prompt rewritten: added Authority Hierarchy section (objective state outranks customer framing), sharpened low/medium boundary to cover routine-with-escalation-risk, three few-shot examples derived from v1 failures.

### Added
- Retry policy on Google Sheets append node (3 tries, 2000ms backoff) after rate-limit incident in eval batch. See FAILURE_LOG, 2026-05-05.

### Eval
- v2 severity accuracy: 80.0% (24/30), up from 76.7% in v1.
- 1 of 7 v1 failures fixed (TH-04559, angry customer no emergency).
- 6 v1 failures persist with reasoning patterns close to v1. Honest analysis in README.

---

## [v1.0-eval] — 2026-05-05

### Eval
- v1 baseline evaluated against 30-ticket held-out set with ground-truth annotation.
- Severity accuracy: 76.7% (23/30). Critical: 4/4 correct, no false negatives.
- Three failure patterns identified: customer self-assessment overweighted, routine-with-escalation-risk underrated, early-warning signals underrated. See FAILURE_LOG, 2026-05-05.

---

## [v1.0-build] — 2026-05-04

### Added
- Webhook trigger at path `support-triage-v1`, receives ticket payloads via curl.
- Two-LLM pipeline: extraction node and scoring node, both gpt-4.1-mini at temperature 0, both with strict JSON Schema output.
- Tier multiplier code node, deterministic JavaScript: `final_priority = severity_score × tier_weight × season_multiplier`.
- German heating-domain context in scoring prompt: heating-season corridor (Oct 1 to Apr 30 per case law), outdoor-temperature thresholds by building energy class, vulnerable-occupant override, safety-signal override, multi-property B2B escalation rule.
- Deterministic season multiplier in code: 1.0 in heating season, 0.7 outside.
- 30 synthetic eval tickets in `test-data/`, ground-truth annotated, covering 16 edge-case categories including prompt injection.
- Workflow exported to `n8n/workflow_v1.json`.

### Verified
- End-to-end pipeline run: Müller emergency ticket (heating off, two children, Tier C, heating season) classified as critical, final_priority 5.6.

## v2.1 — 2026-05-28
- Replaced sub-workflow audit log with webhook-based architecture
- Fixed validator/schema drift (`missing_message` → `missing_body`)
- Fixed pipeline data flow: Edit Fields1 now reads via source-node naming