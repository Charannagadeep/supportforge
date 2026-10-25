# SupportForge — paste into BuilderBase (every field)

Copy each **Answer** block into the matching form field.

---

### Project name
**Answer:**  
SupportForge

---

### One-line pitch
**Answer:**  
SupportForge is a local evidence agent that turns incomplete GPU and AI-server support packs into cited, scored engineering handoffs for Dell/NVIDIA on-call engineers — all inference on the GB10, no cloud LLM.

---

### Repository URL
**Answer:**  
https://github.com/Charannagadeep/supportforge

---

### Demo video URL
**Answer:**  
*(Upload Desktop `SupportForge-Demo-2min.mp4` to YouTube or Google Drive as public/anyone-with-link, then paste that URL here. Keep it off GitHub.)*

Placeholder until you upload:  
`[PASTE_PUBLIC_VIDEO_LINK]`

---

### What you built, and what runs locally
**Answer:**  
SupportForge is a local-first agent console for enterprise GPU / AI-server support.

**Agent workflow**
1. Watches a case pack (environment, nvidia-smi, logs, notes, steps tried).  
2. Audits required evidence against a GPU/serving checklist.  
3. Builds a cited failure timeline and ranked hypotheses with a deterministic rule layer.  
4. Runs a live local LLM investigation grounded in case files (filenames + log-backed claims).  
5. Writes a scored engineering handoff and re-audits when new files arrive (always-on watcher).  
6. Enforces security: path sandbox, tool denials (e.g. shell / GPU reset), secret redaction, audit JSONL.

**Tools / stack**
- FastAPI console UI (`:8787`) + OpenClaw-style skills: evidence-audit, timeline-builder, escalation-handoff  
- OpenShell / NemoClaw sandbox `supportforge` for policy-isolated agent execution on GB10  
- Eval harness (5 golden failure families) so quality is measured, not claimed  

**Inference (reasoning + tool selection) — all local on GB10**
- Primary: **Qwen3.6-35B-A3B-NVFP4** via vLLM on `:8000`  
- USB pack also carries **Nemotron-3-Nano-4B-FP8**  
- **No cloud LLM calls** on the scored / demo path. Laptop Ollama is practice-only before the box.

---

### Walk us through getting started with the DGX Spark
**Answer:**  
Hardware: Dell Pro Max with **GB10** (DGX Spark-class). Software: NemoClaw Express Install + OpenShell + SupportForge + local vLLM.

1. Plug the **NVIDIAHACK** USB (`nvidia-hackathon/`) — models, packages, project, OpenShell `.deb`.  
2. Seed models from USB: **Qwen3.6-35B-A3B-NVFP4** and **Nemotron-3-Nano-4B-FP8**.  
3. Install stack: `curl -fsSL https://www.nvidia.com/nemoclaw.sh | bash` → accept Express Install (**Y**).  
4. From the project on the box: `bash scripts/gb10-bringup.sh supportforge` (HF cache, OpenShell sandbox, console + API key).  
5. Serve the model with vLLM/NIM on `:8000` (Qwen3.6-35B-A3B-NVFP4).  
6. Open `http://<gb10-ip>:8787` — health shows `mode=gb10`, model online.  
7. Run the product arc: CASE-1042 → Reset → Audit → Inject → Investigate → rule/LLM eval → security deny.  
8. Optional isolation: `nemoclaw launch supportforge`.  

Offline OpenShell if needed: `sudo dpkg -i packages/openshell-0.0.116/openshell_0.0.116-1_arm64.deb`.

---

### Pitch deck
**Answer:**  
https://htmlpreview.github.io/?https://github.com/Charannagadeep/supportforge/blob/main/pitch/index.html  

(Repo file: https://github.com/Charannagadeep/supportforge/blob/main/pitch/index.html)

---

### Which resources helped most, and what do you wish you'd had access to?
**Answer:**  
**Helped most:** NVIDIA NemoClaw Express Install docs, OpenShell sandbox packaging, the Spark/GB10 local vLLM path for Qwen3.6 NVFP4, and the offline USB model pack so we were not blocked by download bandwidth on site. The OpenClaw skill layout also made evidence-audit / handoff tools easy to wire.

**Wish we'd had:** A single “golden path” GB10 checklist that pins exact vLLM serve flags for Qwen3.6-35B-A3B-NVFP4, a pre-validated CDI/toolkit evidence sample pack from real NVIDIA support workflows, and earlier access to a shared GB10 so we could spend less time on laptop rehearsal and more on OpenShell policy tuning.

---

### What would have got you there faster?
**Answer:**  
1) Official one-command “serve Qwen3.6-35B-A3B-NVFP4 on GB10 + register OpenShell sandbox” script.  
2) A small set of anonymized real incomplete GPU tickets already mapped to an evidence checklist.  
3) GB10 hardware earlier in the day (USB preload helped, but on-box iteration is still the bottleneck).  
4) Clearer examples of NemoClaw channel + tool-policy patterns for enterprise support agents (deny-by-default shell, allow local inference only).

---

### What model(s) did you move forward with, and for what?
**Answer:**  
- **Qwen3.6-35B-A3B-NVFP4** — primary GB10 model for Investigate + live LLM eval (reasoning over case files, cited narrative).  
- **Nemotron-3-Nano-4B-FP8** — onboard USB pack for fast / lighter local assist and bring-up checks.  
- **Qwen2.5-7B-Instruct (Ollama)** — laptop-only practice before GB10; not used for the scored on-box demo path.

---

### What drove your model choices?
**Answer:**  
We needed a **strong local** model that fits the Dell GB10 / NVFP4 path sponsors emphasize, with enough reasoning quality for cited support investigations — hence Qwen3.6-35B-A3B-NVFP4 on vLLM. Nemotron Nano 4B gives a small NVIDIA-family fallback that loads quickly from USB. The 7B Ollama model exists only so the team can rehearse the product loop on a laptop without waiting for the box. We explicitly avoided cloud LLMs for the scored runtime because case data is private and the hackathon requires on-box inference.

---

### How did you get set up with your models?
**Answer:**  
Pre-downloaded weights onto an exFAT **NVIDIAHACK** USB (`nvidia-hackathon/models/`). On GB10 we seed the Hugging Face / vLLM cache from that USB, Express-install NemoClaw, bring up OpenShell, then serve **Qwen3.6-35B-A3B-NVFP4** on `http://127.0.0.1:8000`. SupportForge auto-detects vLLM and sets `mode=gb10`. Laptop rehearsal uses `ollama pull qwen2.5:7b-instruct` only for practice.

---

### Did you use NVIDIA NemoClaw and/or OpenShell today?
**Answer:**  
Yes — both. NemoClaw Express Install for the GB10 agent runtime; OpenShell sandbox `supportforge` for isolated tools / policy-bounded egress around SupportForge skills and local inference.

---

### If you used NVIDIA NemoClaw and/or OpenShell, how likely are you to recommend it to other developers?
**Answer:**  
**9** / 10

---

### Please share why or provide additional feedback.
**Answer:**  
NemoClaw + OpenShell is the right default for enterprise local agents: Express Install gets you to a runnable box fast, and OpenShell’s isolation matches how support tooling should behave (local inference allowed, arbitrary shell / public exfil denied). The USB + OpenShell `.deb` offline path was critical when network was flaky. Feedback: ship a shorter “support-agent” blueprint (skills + deny-shell policy + vLLM endpoint) so teams spend hours on product logic instead of wiring. Docs for sandbox ↔ localhost:8000 inference were the sharp edge we hit most.

---

### If you used NVIDIA NemoClaw or OpenShell, how secure did you feel building with it?
**Answer:**  
**9** / 10

---

### What influenced your rating? Please share any concerns, positive experiences, or other feedback.
**Answer:**  
**Positive:** Path sandboxing, tool denials (we demo “run shell / reset GPU” → denied), and the mental model of policy-isolated egress made us comfortable putting private-style case bundles on the box. Audit logging in SupportForge plus OpenShell boundaries stacked well.  
**Concerns / wish-list:** Want clearer default policies for “local vLLM only” and more turnkey examples of redacting secrets before any channel egress. Overall we felt substantially safer than a bare agent with open shell on a shared GB10.

---

## Quick copy map

| Form field | Where above |
|------------|-------------|
| Project name | SupportForge |
| One-line pitch | first pitch block |
| Repository URL | github.com/Charannagadeep/supportforge |
| Demo video URL | paste after you upload Desktop MP4 |
| What you built… | long workflow block |
| Getting started DGX Spark | GB10 steps |
| Pitch deck | htmlpreview link |
| Resources / wish | resources block |
| Faster | faster block |
| Models / for what | models block |
| Drove choices | drove block |
| How set up | setup block |
| Used NemoClaw/OpenShell | Yes |
| Recommend 1–10 | 9 |
| Why recommend | why block |
| Secure 1–10 | 9 |
| Why secure | security feedback block |
