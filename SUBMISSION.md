# SupportForge — Dell × NVIDIA AI Hack · submission answers

Paste these into the BuilderBase form. Keep the repo + video links public.

---

## Project name

**SupportForge**

---

## One-line pitch

Local evidence laboratory that turns incomplete GPU/AI-server support packs into cited, scored engineering handoffs — fully on-box with Dell GB10 + OpenShell.

---

## Category

Local AI Agents / Enterprise GPU support (agentic triage on GB10)

---

## Repository URL

https://github.com/Charannagadeep/supportforge

---

## Pitch deck

https://docs.google.com/presentation/d/1Fgwp8xg50VLVt0UCP-l7R1PE8D8N2mpKb32s_1jpSX8/edit?usp=sharing

---

## Demo video URL

Upload the local ≤2 min walkthrough separately (Desktop: `SupportForge-Demo-2min.mp4`) to Drive / YouTube / similar, then paste that public link here.  
**Do not host the demo video on this GitHub repo.**

---

## What you built, and what runs locally

SupportForge is a **local-first agent console** for enterprise GPU / AI-server support.

**Workflow**
1. Ingests a case pack (env, `nvidia-smi`, logs, notes)
2. **Audits** required evidence against a GPU/serving checklist
3. Builds a **cited timeline** and ranked hypotheses (deterministic rule layer)
4. Runs a **live local LLM** investigation grounded in case files (not a chat guess)
5. Emits a scored **engineering handoff** + re-audits when files change (always-on watcher)
6. Enforces a **security boundary**: path sandbox, tool denials, redaction, audit JSONL

**What runs locally (no cloud LLM for scored runtime)**
- FastAPI console UI at `:8787`
- Rule engine + 7 live cases + 5 golden evals
- Real NVIDIA Container Toolkit corpus (80 cleaned issues; ~60% incomplete)
- Laptop practice: Ollama `qwen2.5:7b-instruct`
- **GB10 production path:** vLLM **Qwen3.6-35B-A3B-NVFP4** (+ Nemotron Nano 4B on USB) behind OpenShell / NemoClaw sandbox `supportforge`

Confirm: all demo inference is local — Anthropic is opt-in for laptop coding only, never the scored path.

---

## Walk us through getting started with the DGX Spark / GB10

1. Plug the **NVIDIAHACK** USB (`nvidia-hackathon/`) into the Dell GB10 / DGX Spark  
2. Copy or mount `models/` (Qwen3.6-35B-A3B-NVFP4 + Nemotron-3-Nano-4B-FP8)  
3. Express Install NemoClaw: `curl -fsSL https://www.nvidia.com/nemoclaw.sh | bash` → accept **Y**  
4. From the project: `bash scripts/gb10-bringup.sh supportforge`  
   - Seeds HF cache, installs OpenShell sandbox, starts console with API key  
5. Start / confirm vLLM on `:8000` serving Qwen3.6-35B-A3B-NVFP4  
6. Open `http://<gb10>:8787` — health shows `mode=gb10`, GB10 pack online  
7. Demo: CASE-1042 → Reset → Audit (~60%) → Inject (100%) → Investigate → Run live LLM eval → ask shell/reset GPU (denied)  
8. Optional: `nemoclaw launch supportforge` for isolated agent tools  

Offline OpenShell fallback: `sudo dpkg -i packages/openshell-0.0.116/openshell_0.0.116-1_arm64.deb`

---

## What model(s) did you move forward with, and for what?

| Model | Where | Role |
|-------|--------|------|
| **Qwen3.6-35B-A3B-NVFP4** | GB10 vLLM `:8000` | Primary scored investigate + live LLM eval |
| **Nemotron-3-Nano-4B-FP8** | GB10 USB pack | Fast / fallback local assist |
| **Qwen2.5-7B-Instruct** (Ollama) | Laptop only | Practice path before GB10 |

We did **not** use cloud LLMs for the scored runtime.

---

## Extra answers (if the form has more of the 17 fields)

**Problem**  
Support tickets for NVIDIA GPU servers arrive incomplete. Engineers cannot start until environment, `nvidia-smi`, logs, and a failure timeline exist.

**Why local**  
Case bundles contain hostnames, paths, and proprietary config — they should not leave the premises.

**Stack**  
NemoClaw + OpenClaw + OpenShell on Dell GB10; SupportForge console + skills (`evidence-audit`, `timeline-builder`, `escalation-handoff`).

**How we measure**  
```bash
bash scripts/start-console.sh
bash scripts/run-eval.sh rule   # deterministic goldens
bash scripts/run-eval.sh llm    # live local model
```
Rule eval: **100% pass** on 5 golden families (OOM, Xid 79, NCCL, driver mismatch, ECC).

**Security**  
Shell/GPU-reset style tool use is denied; path sandbox; secret redaction; `workspace/memory/security-audit.jsonl`. Details: `SECURITY.md`.

**Team**  
Charannagadeep (lead) · shivanisam · vini104 · Anshi-12 · JadaSange · praveen-sud · jaswanthkrishnaakula — see `TASKS.md`.

**Demo script (≤2 min)**  
Website walkthrough with cursor + voice: Reset → Audit → Inject → Investigate → Eval → Security deny → NVIDIA corpus. Host the MP4 outside GitHub.

---

## Links checklist

| Item | URL / path |
|------|------------|
| Repo | https://github.com/Charannagadeep/supportforge |
| Pitch | https://docs.google.com/presentation/d/1Fgwp8xg50VLVt0UCP-l7R1PE8D8N2mpKb32s_1jpSX8/edit?usp=sharing |
| Demo video | External host only (not this repo) |
| Security | `SECURITY.md` |
| Benchmark | `BENCHMARK.md` |
| GB10 bring-up | `scripts/gb10-bringup.sh` |
