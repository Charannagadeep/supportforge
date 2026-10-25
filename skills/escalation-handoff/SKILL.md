---
name: escalation-handoff
description: Produce or refresh an engineering handoff package from audit + timeline + runbooks. Source-referenced; lists unknowns and next checks.
---

# Escalation handoff

## When to run

After evidence-audit (always). After timeline-builder when logs exist. Also when new evidence arrives.

## Procedure

1. Read `audit.json`, `timeline.md` (if any), `customer/*`, and matching docs in `workspace/runbooks/`.
2. Fill `workspace/templates/handoff.md` → write `workspace/outbox/<ID>-handoff.md`.
3. Sections required:
   - **Summary** (3 lines max)
   - **Completeness** (% + missing list)
   - **Environment** (only from files; else Unknown)
   - **Timeline** (link/embed short version with citations)
   - **Observations** (facts only)
   - **Hypotheses** (ranked; each must note supporting or missing evidence)
   - **Unknowns**
   - **Next checks** (concrete)
   - **Customer requests** (copy from requests file)
4. If messaging channel available, post: case id, completeness %, handoff path.

## Quality bar

A good handoff is a **checked case package**, not a chatty summary. Engineers should see what was verified vs guessed.
