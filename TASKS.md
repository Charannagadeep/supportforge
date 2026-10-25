# SupportForge — team tasks (hackathon)

Repo: https://github.com/Charannagadeep/supportforge  

**Everyone:** accept the GitHub invite → clone → create a branch → do your task → open a PR → merge (or ask lead).

```bash
git clone https://github.com/Charannagadeep/supportforge.git
cd supportforge
git checkout -b yourname/task-short-name
# ... work ...
git add -A
git commit -m "Describe what you did"
git push -u origin yourname/task-short-name
# Then open a Pull Request on GitHub
```

Install / run UI (all members):

```bash
uv venv .venv && source .venv/bin/activate
uv pip install -e .
bash scripts/start-console.sh
# open http://127.0.0.1:8787
```

---

## Assignments

### 1) Charannagadeep (lead)
**Own:** repo health, merges, demo readiness, BuilderBase submission  
- Review/merge PRs  
- Keep demo working end-to-end  
- Fill team names in `SUBMISSION.md`  
- Record or coordinate the ≤2 min video  
- Push final tag / ensure main is clean before 6:00 PM  

Branch: `lead/submission`

---

### 2) shivanisam — Frontend / console UX
**Own:** `app/static/`  
**Goal:** Make the demo UI clearer and more judge-friendly  

Do:
- Improve empty states (Requests / Handoff before audit)  
- Show a visible error banner instead of browser alerts when offline  
- Add a “Demo progress” checklist on the page (Reset → Audit → Inject → Handoff)  
- Make mobile/narrow layout usable  
- Optional: favicon  

**Done when:** Demo flow is obvious without reading README  
Branch: `shivanisam/ui-polish`  
PR title: `ui: polish console demo flow`

---

### 3) vini104 — Evidence engine
**Own:** `app/engine.py`, `workspace/runbooks/`  
**Goal:** Stronger audits and smarter hypotheses  

Do:
- Improve completeness scoring / weak-file detection  
- Add 1–2 more runbooks (e.g. driver mismatch, disk-full)  
- Better timeline extraction (more log patterns)  
- Ensure CASE-1088 produces an Xid-focused hypothesis after inject  

**Done when:** `CASE-1042` and `CASE-1088` both produce solid handoffs  
Branch: `vini104/engine-runbooks`  
PR title: `engine: stronger audit, timeline, runbooks`

---

### 4) Anshi-12 — Agent chat
**Own:** `app/agent.py`  
**Goal:** Natural commands that drive the demo  

Do:
- Support more phrasings (“check case”, “what’s missing”, “refresh handoff”)  
- Add `help` that lists cases + suggested next step  
- After audit, reply with a short markdown table of evidence  
- Optional: if `ANTHROPIC_API_KEY` is set, prettier explanations (keep evidence local)  

**Done when:** Full demo works by chat chips/commands alone  
Branch: `Anshi-12/agent-chat`  
PR title: `agent: richer laptop chat commands`

---

### 5) JadaSange — Demo cases & realism
**Own:** `cases/`  
**Goal:** Believable support packs for the live demo  

Do:
- Enrich CASE-1042 / CASE-1088 customer descriptions (account, impact, urgency)  
- Add a third mini case `CASE-1101` (e.g. slow inference / wrong CUDA) with incomplete + complete packs  
- Register new case in engine seed paths if needed  
- Keep logs short but realistic  

**Done when:** 3 cases appear in the UI and demo inject works for 1042  
Branch: `JadaSange/demo-cases`  
PR title: `cases: richer demos + CASE-1101`

---

### 6) Praveen-sud — Pitch, video script, submission write-up
**Own:** `pitch/`, `demo/SCRIPT.md`, `SUBMISSION.md`  
**Goal:** Judging package  

Do:
- Tighten pitch slides in `pitch/index.html` (problem → solution → demo → ask)  
- Finalize 2-minute video script with exact UI clicks  
- Complete `SUBMISSION.md` (problem, solution, why local, metrics)  
- Add a one-page “judge crib sheet” `demo/JUDGE-NOTES.md`  

**Done when:** Someone can record the video from the script alone  
Branch: `praveen-sud/pitch-submission`  
PR title: `docs: pitch, video script, submission`

---

### 7) jaswanthkrishnaakula — GB10 / NemoClaw integration path
**Own:** `scripts/sunday-setup.sh`, `skills/`, `CHANNELS.md`  
**Goal:** Clear path when/if GB10 is available; laptop still works  

Do:
- Improve `sunday-setup.sh` copy paths + echo instructions  
- Polish OpenClaw skill docs (`skills/*/SKILL.md`) so prompts match the UI demo  
- Document Slack/Telegram setup steps more clearly in `CHANNELS.md`  
- Add `docs/GB10.md` with Express Install + how to point agent at this repo  

**Done when:** README links to a crisp GB10 runbook; skills match CASE-1042 language  
Branch: `jaswanthkrishnaakula/gb10-skills`  
PR title: `gb10: setup script + skills + channels docs`

---

## Rules (so we don’t break each other)

1. **One branch per person** — don’t push straight to `main` unless lead says so  
2. **Don’t rewrite someone else’s owned folder** without asking  
3. **Test before PR:** `bash scripts/start-console.sh` + Reset → Audit → Inject  
4. **Small PRs** — easier to merge before 6:00 PM  
5. **No secrets** in git (no API keys, no real customer logs)  

## Merge order (suggested)

1. engine / cases  
2. agent  
3. ui  
4. pitch/docs  
5. gb10 docs  

Lead merges everything to `main` and locks for video + submit.
