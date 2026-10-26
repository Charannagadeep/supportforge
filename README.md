# SupportForge

**Local evidence laboratory** for enterprise GPU / AI-server support — cited handoffs, live local LLM, **measured** quality.

Dell × NVIDIA hackathon · **GB10-winning path** (Qwen3.6-35B NVFP4 + OpenShell) · laptop still works for practice.

> Not a chatbot summary. A **checked, scored case package** with evidence audit, log-cited timeline, live investigation, and a reproducible eval harness.

---

## Team

| GitHub | Role |
|--------|------|
| Charannagadeep | Lead / repo |
| shivanisam | Collaborator |
| vini104 | Collaborator |
| Anshi-12 | Collaborator |
| JadaSange | Collaborator |
| praveen-sud | Collaborator |
| jaswanthkrishnaakula | Collaborator |

**Assigned tasks for everyone:** see [`TASKS.md`](TASKS.md) (branch names + done criteria).

---

## Prerequisites

- **macOS or Linux**
- **Python 3.10+** (3.12 recommended)
- **[uv](https://docs.astral.sh/uv/)** (fast installer) **or** plain `pip`
- Git

Install `uv` (recommended):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## 1. Clone the repo

```bash
git clone https://github.com/Charannagadeep/supportforge.git
cd supportforge
```

If you were invited as a collaborator, accept the GitHub invite email/notification first.

---

## 2. Install dependencies

### Option A — `uv` (recommended)

```bash
uv venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
uv pip install -e .
```

### Option B — `pip`

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

---

## 3. Start the backend + open the frontend

The UI is served by the same FastAPI app (no separate React build).

```bash
bash scripts/start-console.sh
```

Or manually:

```bash
source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8787
```

### Security configuration

Full control list: [`SECURITY.md`](SECURITY.md) · verify: `bash scripts/verify-security.sh`

The console binds to **127.0.0.1** by default. Loopback requests work without a key; non-loopback requests require `X-API-Key`. For shared GB10:

```bash
export SUPPORTFORGE_API_KEY='replace-with-a-long-random-secret'
export SUPPORTFORGE_ALLOWED_HOSTS='gb10.example.internal,127.0.0.1'
export SUPPORTFORGE_HOST='0.0.0.0'
bash scripts/start-console.sh
```

Browser: `localStorage.setItem("supportforge_api_key", "…")` and optional `supportforge_user`.  
CORS off unless `SUPPORTFORGE_CORS_ORIGINS` is set. External Anthropic assist is off unless `SUPPORTFORGE_ALLOW_EXTERNAL_ASSIST=1`. Audit: `workspace/memory/security-audit.jsonl`.

### Open the frontend

In your browser go to:

**http://127.0.0.1:8787**

You should see status **local · online** (laptop mode).

> Keep the terminal running while you use the UI. Stopping the process takes the site offline.

---

## 4. Local LLM (required for the winning demo)

SupportForge audits evidence with a deterministic engine, then runs a **live local model** for the investigation narrative.

```bash
# Install Ollama (once), then:
open -a Ollama
ollama pull qwen2.5:7b-instruct
```

Health should show `model_online: true`:

```bash
curl -s http://127.0.0.1:8787/api/health | jq .
```

| Provider | When |
|----------|------|
| **Ollama** (default) | Laptop — auto-detects `qwen2.5:7b-instruct` |
| **vLLM** `:8000` | GB10 — Qwen3.6-NVFP4 auto-preferred if up |
| **Anthropic** | Optional — set `ANTHROPIC_API_KEY` |

Override: `SUPPORTFORGE_MODEL`, `SUPPORTFORGE_LLM_BASE`.


---

## 5. Pitch deck

Public slides (Google Drive):  
https://docs.google.com/presentation/d/1sG1W3k0peXW89u2PXFHas8LDYpcyqtiX/edit?usp=sharing

Local HTML backup: `pitch/index.html`

---

## Project layout

```text
supportforge/
  app/                 # FastAPI API + static frontend
    agent.py           # Agent (audit + LLM investigate)
    engine.py          # Evidence audit / timeline / handoff
    llm.py             # Ollama / vLLM / Anthropic providers
    main.py            # HTTP routes
    static/            # Frontend (HTML/CSS/JS)
  cases/               # Demo source packs (incomplete + complete)
  skills/              # OpenClaw skills for GB10 / NemoClaw
  workspace/           # Live cases, runbooks, outbox
  scripts/             # start-console, walkthrough, GB10 setup
  pitch/               # HTML pitch
  demo/SCRIPT.md       # Video script
  SUBMISSION.md        # Hackathon write-up
  SOUL.md AGENTS.md HEARTBEAT.md
```

---

## API cheatsheet

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Frontend |
| GET | `/api/health` | Health + model provider |
| GET | `/api/provider` | Active LLM |
| GET | `/api/cases` | List cases |
| POST | `/api/cases/{id}/audit` | Run evidence audit |
| POST | `/api/cases/{id}/investigate` | Audit + live LLM |
| POST | `/api/demo/reset` | Reset CASE-1042 incomplete |
| POST | `/api/demo/inject-complete` | Add missing evidence |
| POST | `/api/chat` | Agent message `{"message":"..."}` |
| GET | `/api/cases/{id}/handoff` | Handoff markdown |
| GET | `/api/cases/{id}/llm-report` | Live model report |

Example:

```bash
curl -s http://127.0.0.1:8787/api/health
curl -s -X POST http://127.0.0.1:8787/api/chat \
  -H 'content-type: application/json' \
  -d '{"message":"Audit CASE-1042"}'
```

---

## Live case lab + eval

| Case | Story |
|------|--------|
| **CASE-1042** | Serving CUDA OOM; abandoned `train_scratch.py` |
| **CASE-1088** | Training fault; dmesg **Xid 79** |
| **CASE-1101** | Multi-node fine-tune; **NCCL** hang |
| **CASE-1120** | Host/container **CUDA driver mismatch** |
| **CASE-1155** | NaN logits from **ECC / remapped rows** |
| **CASE-2163** | Real GH issue — CDI/NVML fail when GPUs on vfio-pci |
| **CASE-2161** | Real GH issue — `libnvsdm` missing from management CDI |

**Real NVIDIA corpus:** `data/nvidia_container_toolkit_issues.csv` (80 cleaned toolkit issues).  
UI tab **NVIDIA corpus** · API `/api/corpus/stats` — ~60% of real issues are under 70% evidence (same gaps we audit).

```bash
bash scripts/run-eval.sh rule   # deterministic, ~1s
bash scripts/run-eval.sh llm    # live Ollama across goldens
```

Methodology: [`BENCHMARK.md`](BENCHMARK.md) · Security: [`SECURITY.md`](SECURITY.md) · Write-up: [`SUBMISSION.md`](SUBMISSION.md)

---

## GB10 bring-up (winning path — run ON the box)

Plug **NVIDIAHACK** USB (or rsync `~/Desktop/Nvidia`), then:

```bash
cd /path/to/supportforge   # or nvidia-hackathon/project
bash scripts/gb10-bringup.sh supportforge
```

That seeds HF cache with **Qwen3.6-35B-A3B-NVFP4**, wires OpenShell skills/cases, starts the console on `:8787` with an API key, and prefers vLLM on `:8000`.

Manual pieces:

```bash
# Express Install once (Spark profile)
curl -fsSL https://www.nvidia.com/nemoclaw.sh | bash   # Y = Express
bash scripts/install-openshell.sh supportforge
SUPPORTFORGE_RUNTIME=gb10 SUPPORTFORGE_API_KEY='…' bash scripts/start-console.sh
nemoclaw launch supportforge
```

Judge arc: Reset → Audit (~60%) → Inject → **Investigate on 35B** → live LLM eval → shell denied → OpenShell isolation.

## OpenShell / NemoClaw (laptop practice)

```bash
bash scripts/install-openshell.sh supportforge
nemoclaw launch supportforge
```

Isolation: sandbox reaches local inference only; arbitrary public HTTPS is blocked. Skills: `evidence-audit`, `timeline-builder`, `escalation-handoff`. Channels: `CHANNELS.md`.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Browser shows **offline** / Load failed | Terminal not running — start `bash scripts/start-console.sh` again |
| Port 8787 in use | `lsof -i :8787` then stop the old process, or use `--port 8790` |
| `uv` / `python` not found | Install Python 3.10+ and/or uv (see Prerequisites) |
| Blank page | Hard refresh (`Cmd+Shift+R`) · confirm http://127.0.0.1:8787 |
| `model offline` / `no_models` | `open -a Ollama` then `ollama pull qwen2.5:7b-instruct` |
| Investigate hangs | First token load can take 30–90s on CPU/Metal — wait |

---

## Hackathon submit

Paste-ready answers: **[`SUBMISSION.md`](SUBMISSION.md)**

| Field | Value |
|-------|--------|
| Repo | https://github.com/Charannagadeep/supportforge |
| Pitch | [Google Slides](https://docs.google.com/presentation/d/1sG1W3k0peXW89u2PXFHas8LDYpcyqtiX/edit?usp=sharing) |
| Write-up | [`SUBMISSION.md`](SUBMISSION.md) |

Demo video is kept local (not in this repo). Host it separately for the form (Drive / YouTube / etc.).

---

## License

Hackathon / demo use. Sample logs are synthetic.
