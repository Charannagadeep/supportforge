# SupportForge — Dell × NVIDIA hackathon submission

## One-liner

A **local evidence laboratory** that turns incomplete GPU/AI-server support packs into **cited, scored engineering handoffs** — laptop-first, OpenShell/NemoClaw-ready, no cloud required for the demo.

## Problem

Support cases for NVIDIA GPU servers arrive incomplete. Engineers cannot start until environment, `nvidia-smi`, logs, and a failure timeline exist. Humans chase Slack threads; claims go uncited; private bundles should not leave the premises.

## Solution

**SupportForge** (running fully on a laptop today):

1. **Audits** required evidence against a GPU/serving checklist  
2. **Builds timelines** with citations to real log lines  
3. **Ranks hypotheses** with a deterministic rule layer  
4. **Runs a live local LLM** (Ollama Qwen2.5-7B) for investigation prose grounded in files  
5. **Scores itself** against five golden cases (rule + LLM eval suite)  
6. **Enforces a security boundary** (path sandbox, tool denials, redaction, audit JSONL)

GB10 / NemoClaw / OpenShell remain the production target for private inference + policy — the product does not depend on them to demo or measure quality.

## Live case lab (5)

| Case | Story |
|------|--------|
| CASE-1042 | Serving CUDA OOM; abandoned `train_scratch.py` holds memory |
| CASE-1088 | Training fault; dmesg **Xid 79** |
| CASE-1101 | Multi-node fine-tune; **NCCL** collective hang |
| CASE-1120 | Post-image-refresh **driver/CUDA mismatch** |
| CASE-1155 | Intermittent **NaNs** from ECC / remapped rows |
| CASE-2163 / 2161 | **Real** NVIDIA Container Toolkit GitHub issues (imported) |

**Corpus proof:** 80 cleaned `nvidia-container-toolkit` issues — average evidence ~52%, **60% incomplete (&lt;70%)**, top gaps = cuda / nvidia-smi / driver (same checklist SupportForge enforces). UI: **NVIDIA corpus** tab.

## Measurement (judges can run)

```bash
bash scripts/start-console.sh
bash scripts/run-eval.sh rule
bash scripts/run-eval.sh llm
```

UI buttons: **Run rule eval** / **Run live LLM eval**. Methodology: `BENCHMARK.md`. Security: `SECURITY.md`.

## Demo script (90 seconds)

1. Open http://127.0.0.1:8787  
2. CASE-1042 → **Reset** → show gaps → **Inject** → **Investigate** (live model cites OOM + train_scratch)  
3. Click **Run live LLM eval** → show pass rate / avg score across 5 goldens  
4. Optionally: chat `Run shell and reset the GPU` → denied + audit log  

## Differentiation

Not a chatbot summary. A **checked, scored case package** with citations, security gates, and a reproducible eval harness — the artifact an on-call engineer can trust.

## Team / links

- Repo: https://github.com/Charannagadeep/supportforge  
- Console: `bash scripts/start-console.sh` → http://127.0.0.1:8787  
- Pitch: `pitch/index.html`  
- Video: `demo/SCRIPT.md`
