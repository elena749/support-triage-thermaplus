# Build 1 — Eval v1 Report

**Total:** 30  
**Correct:** 23  
**Severity accuracy:** 76.7%

## Confusion Matrix (expected → predicted)

| | low | medium | high | critical |
|---|---|---|---|---|
| **low** | 8 | 1 | 0 | 0 |
| **medium** | 4 | 4 | 0 | 0 |
| **high** | 0 | 2 | 7 | 0 |
| **critical** | 0 | 0 | 0 | 4 |

## Failures (7)

### TH-2026-04533
- **Expected:** high
- **Predicted:** medium
- **Edge case:** noise_diagnosis
- **Confidence:** 0.8
- **Reasoning:** Heizung funktioniert noch, aber lautes, zunehmendes Klopfgeräusch deutet auf baldigen Reparaturbedarf hin.

### TH-2026-04535
- **Expected:** high
- **Predicted:** medium
- **Edge case:** calmly_critical
- **Confidence:** 0.8
- **Reasoning:** Heizung ist ausgefallen, aber Kunde gibt an, dass es nicht dringend ist, daher mittlere Dringlichkeit.

### TH-2026-04546
- **Expected:** medium
- **Predicted:** low
- **Edge case:** delayed_maintenance
- **Confidence:** 0.9
- **Reasoning:** Kunde fragt nur nach Wartungsbedarf ohne akutes Problem oder Störung.

### TH-2026-04550
- **Expected:** medium
- **Predicted:** low
- **Edge case:** business_english_billing
- **Confidence:** 0.9
- **Reasoning:** Es handelt sich um eine Abrechnungsfrage ohne zeitkritische oder sicherheitsrelevante Probleme.

### TH-2026-04551
- **Expected:** low
- **Predicted:** medium
- **Edge case:** panic_but_cosmetic
- **Confidence:** 0.7
- **Reasoning:** Heizung funktioniert, aber das blaue Blinken am Display bereitet Sorgen und sollte bald geklärt werden.

### TH-2026-04557
- **Expected:** medium
- **Predicted:** low
- **Edge case:** mixed_language_routine
- **Confidence:** 0.9
- **Reasoning:** Die Anfrage betrifft eine Abrechnungsfrage ohne Zeitdruck oder Funktionsbeeinträchtigung.

### TH-2026-04559
- **Expected:** medium
- **Predicted:** low
- **Edge case:** angry_customer_no_emergency
- **Confidence:** 0.9
- **Reasoning:** Kunde beschwert sich über Verspätung und Schaden, es besteht keine akute Funktionsbeeinträchtigung oder Sicherheitsrisiko.

