# SupportForge — submission write-up

## Team
_Fill before submit: names + team lead (prize ships to lead)_

## Problem

Enterprise GPU / AI-server cases arrive incomplete. Engineers cannot investigate until environment, logs, prior steps, and a failure timeline exist. That chase burns hours and delays customers. NVIDIA triage guidance and Dell support-bundle procedures both emphasize collecting this evidence — humans still stitch it together.

## Solution

**SupportForge** is an always-on local agent (NemoClaw + OpenClaw + OpenShell on Dell Pro Max with GB10) that:

1. Watches case folders  
2. Audits required evidence against a GPU/serving checklist  
3. Builds timelines with citations to real log lines  
4. Produces engineering handoffs (observations, hypotheses, unknowns, next checks)  
5. Re-runs when new evidence arrives  

Includes a local **ops console** for live demos and a deterministic evidence engine as a reliable fallback.

## Why local

Support bundles contain internal hostnames, paths, and proprietary configuration. Inference and packaging stay on the GB10. External sharing remains a separate approved step.

## Differentiation

Complementary to Dell automated support and NVIDIA diagnostic tooling. Focused on **evidence validation and investigation handoff**, not replacing vendor collectors or becoming a generic chatbot.

## Demo

- **CASE-1042:** incomplete serving crash → missing env + nvidia-smi → complete handoff citing CUDA OOM and abandoned `train_scratch.py`  
- **CASE-1088:** training fault → Xid 79 in dmesg (second scenario)

## Measure

- Case-preparation time  
- Required-field completeness %  
- Whether each technical claim has a citation  

## Links

- Repo: this `project/` directory  
- Console: `bash scripts/start-console.sh` → http://GB10:8787  
- Pitch: `pitch/index.html`  
- Video script: `demo/SCRIPT.md`
