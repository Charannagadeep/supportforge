# SupportForge

**Always-on local support investigation agent** for enterprise GPU / AI-server cases.

Dell × NVIDIA hackathon · laptop demo now · **NemoClaw + OpenClaw + OpenShell** on GB10 when available.

> Not a chatbot summary. A **checked case package** with evidence audit, log-cited timeline, and engineering handoff.

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

Suggested task split (pick one and open a PR):

1. **Console / UI** — polish `app/static/`, demo UX  
2. **Evidence engine** — `app/engine.py`, checklists, runbooks  
3. **Agent chat** — `app/agent.py`, prompts, chips  
4. **Demo cases** — `cases/CASE-*`, realism, second scenarios  
5. **Pitch / video / submission** — `pitch/`, `demo/SCRIPT.md`, `SUBMISSION.md`  
6. **GB10 / NemoClaw** — `scripts/sunday-setup.sh`, `skills/`, channels  

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

### Open the frontend

In your browser go to:

**http://127.0.0.1:8787**

You should see status **local · online** (laptop mode).

> Keep the terminal running while you use the UI. Stopping the process takes the site offline.

---

## 4. Run the 2-minute demo

On the page:

1. Click **Reset demo** (or agent chip **Reset demo**)  
2. Click **Audit CASE-1042** (or **Run evidence audit**) → ~**60%**, missing env + `nvidia-smi`  
3. Click **Inject missing evidence** → **100%**, hypotheses cite CUDA OOM + `train_scratch.py`  
4. Open the **Handoff** tab and read citations  

Agent chat examples:

```text
Reset demo
Audit CASE-1042 and prepare the engineering handoff
Inject missing evidence
List cases
```

### CLI demo (no browser)

```bash
bash scripts/demo-walkthrough.sh
```

---

## 5. Pitch deck (optional)

```bash
open pitch/index.html        # macOS
# or open the file in any browser
```

---

## Project layout

```text
supportforge/
  app/                 # FastAPI API + static frontend
    agent.py           # Laptop agent (chat commands)
    engine.py          # Evidence audit / timeline / handoff
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
| GET | `/api/health` | Health check |
| GET | `/api/cases` | List cases |
| POST | `/api/cases/{id}/audit` | Run evidence audit |
| POST | `/api/demo/reset` | Reset CASE-1042 incomplete |
| POST | `/api/demo/inject-complete` | Add missing evidence |
| POST | `/api/chat` | Agent message `{"message":"..."}` |
| GET | `/api/cases/{id}/handoff` | Handoff markdown |

Example:

```bash
curl -s http://127.0.0.1:8787/api/health
curl -s -X POST http://127.0.0.1:8787/api/chat \
  -H 'content-type: application/json' \
  -d '{"message":"Audit CASE-1042"}'
```

---

## Demo cases

| Case | Story |
|------|--------|
| **CASE-1042** | Model-serving CUDA OOM; abandoned `train_scratch.py` holds memory |
| **CASE-1088** | Training fault; dmesg shows **Xid 79** |

---

## GB10 / NemoClaw (optional later)

Only when you have a Dell Pro Max with GB10:

```bash
curl -fsSL https://www.nvidia.com/nemoclaw.sh | bash   # Express Install = Y
bash scripts/sunday-setup.sh my-assistant
bash scripts/start-console.sh
```

Copy `skills/` + `workspace/` into the OpenClaw sandbox. Optional Slack/Telegram: see `CHANNELS.md`.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Browser shows **offline** / Load failed | Terminal not running — start `bash scripts/start-console.sh` again |
| Port 8787 in use | `lsof -i :8787` then stop the old process, or use `--port 8790` |
| `uv` / `python` not found | Install Python 3.10+ and/or uv (see Prerequisites) |
| Blank page | Hard refresh (`Cmd+Shift+R`) · confirm http://127.0.0.1:8787 |

---

## Hackathon submit

- Repo: this GitHub project  
- Video ≤2 min — `demo/SCRIPT.md`  
- Write-up — `SUBMISSION.md`  
- Pitch — `pitch/index.html`  
- Deadlines (PT): GB10 return **5:30** · submit **6:00** · deck **7:00** if Top 8  

---

## License

Hackathon / demo use. Sample logs are synthetic.
