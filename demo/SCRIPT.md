# Demo script — SupportForge

**Target:** ≤2 min video · 3 min live (+2 Q&A if Top 8)

## Cold open (15s)

“SupportForge is an always-on local agent for enterprise support. When GPUs and model servers fail, engineers drown in incomplete cases. We keep private bundles on the Dell Pro Max GB10 and turn them into source-referenced handoffs.”

## Live (90–120s)

1. Show folder `workspace/cases/CASE-1042` — only `serving.log` + customer notes.  
2. Prompt agent: **“Audit CASE-1042 and prepare engineering handoff.”**  
3. Show output: completeness ~40–60%, **missing environment.json + nvidia-smi.txt**, requests file.  
4. Copy from `demo-complete` (or `cases/CASE-1042-complete`) into the live case.  
5. Prompt: **“New evidence arrived — refresh the handoff.”**  
6. Show updated handoff: timeline with CUDA OOM citation + hypothesis that `train_scratch.py` holds ~78 GB — next check kill/confirm abandoned job.

## Close (15s)

“Not another chatbot summary — a checked case package. Local inference, OpenShell sandbox, Dell + NVIDIA support workflows. That’s SupportForge.”

## Backup if agent is slow

Open precomputed `demo/EXPECTED-HANDOFF-AFTER.md` and narrate the same arc from files (still honest: show live audit script).
