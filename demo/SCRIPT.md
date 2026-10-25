# Demo script — SupportForge Lab

**Target:** ≤3 min video · 90s live judge arc  
**Submit this:** [`video/live/SupportForge-Website-Demo.mp4`](video/live/SupportForge-Website-Demo.mp4)  
(~2:30, **real website screen recording** + friendly Indian English voice · Tara)  
Also on Desktop: `~/Desktop/SupportForge-Website-Demo.mp4`

Rebuild website recording:
```bash
# console must be up on :8787
cd project
say -v Tara -r 155 -o demo/video/live/audio/narration.aiff "$(cat demo/video/live/narration.txt)"
afconvert -f WAVE -d LEI16@44100 demo/video/live/audio/narration.aiff demo/video/live/audio/narration.wav
.venv/bin/python3 demo/video/live/record_demo.py
# then mux with ffmpeg (see prior assemble step) or re-run the mux commands in chat history
```

## Cold open (0:00–0:28)

“Support cases for GPU servers arrive incomplete. SupportForge is a **local evidence lab** — it audits packs, cites logs, runs a live local model, and **scores itself**. No GB10 required.”

## Live console (0:28–0:53)

Open http://127.0.0.1:8787 — lab online · Ollama Qwen2.5-7B · 7 cases / 5 goldens / 80 corpus issues · **60% incomplete**.

## Audit gaps (0:53–1:16)

**CASE-1042 → Reset → Audit** — ~60%, missing env + `nvidia-smi`.

## Inject + investigate (1:16–1:40)

**Inject → 100%** · rule cites CUDA OOM + `train_scratch.py` · **Investigate** → live LLM report with citations.

## Measured quality (1:40–2:03)

**Run rule eval** — 5/5 · avg **95**. (Optional: live LLM eval.) Judges reproduce with `bash scripts/run-eval.sh`.

## Security + OpenShell (2:03–2:25)

Chat `Run shell and reset the GPU` → **Denied**. Path sandbox · audit JSONL. OpenShell/NemoClaw = policy-isolated egress on laptop.

## Close (2:25–2:35)

“Not a chatbot paste. A checked, scored handoff — laptop today, OpenShell when you need policy. That’s SupportForge.”

## Backup if LLM is cold

Click **Run rule eval** (sub-second, 100% on goldens) and narrate CASE-1042 handoff from the Handoff tab.
