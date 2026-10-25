# Demo script — SupportForge Lab

Local walkthrough for the console UI (video stays off-repo).

## Cold open

Support cases for GPU servers arrive incomplete. SupportForge is a **local evidence lab** — it audits packs, cites logs, runs a live local model, and **scores itself**.

## Console

Open http://127.0.0.1:8787 — lab online · local model · 7 cases / 5 goldens / 80 corpus issues · **~60% incomplete**.

## Audit gaps

**CASE-1042 → Reset → Audit** — ~60%, missing env + `nvidia-smi`.

## Inject + investigate

**Inject → 100%** · rule cites CUDA OOM + `train_scratch.py` · **Investigate** → live LLM report with citations.

## Measured quality

**Run rule eval** — 5/5 · avg **95**. Optional: live LLM eval. Reproduce with `bash scripts/run-eval.sh`.

## Security + OpenShell

Chat `Run shell and reset the GPU` → **Denied**. Path sandbox · audit JSONL. OpenShell/NemoClaw = policy-isolated egress.

## Close

Not a chatbot paste. A checked, scored handoff — laptop today, stronger on GB10 with OpenShell.
