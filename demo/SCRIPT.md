# Demo script — SupportForge Lab

**Target:** ≤2 min video · 90s live judge arc

## Cold open (10s)

“Support cases for GPU servers arrive incomplete. SupportForge is a **local evidence lab** — it audits packs, cites logs, runs a live local model, and **scores itself** on five golden failures. No GB10 required for this demo.”

## Live (70s)

1. Open http://127.0.0.1:8787 — show metrics strip (5 cases / 5 goldens).  
2. **CASE-1042 → Reset → Audit** — gaps (env + nvidia-smi).  
3. **Inject → Investigate** — live Qwen cites CUDA OOM + `train_scratch.py`.  
4. Click **Run live LLM eval** — pass rate + avg score across 5 families (OOM, Xid, NCCL, driver mismatch, ECC).  
5. Optional spike: chat `Run shell and reset the GPU` → **Denied** (security gate).

## Close (10s)

“Not a chatbot paste. A checked, scored handoff — laptop today, OpenShell/NemoClaw when you need policy isolation. That’s SupportForge.”

## Backup if LLM is cold

Click **Run rule eval** (sub-second, 100% on goldens) and narrate CASE-1042 handoff from the Handoff tab.
