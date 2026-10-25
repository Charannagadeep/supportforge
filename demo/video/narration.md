# SupportForge — Judge demo narration (~3:00)

## Beat 01 — Cold open (0:00–0:25)
Welcome, judges. This is SupportForge — a local evidence laboratory for enterprise GPU and AI-server support.
Cases arrive incomplete. Engineers cannot start until environment, nvidia-smi, logs, and a failure timeline exist.
SupportForge audits the pack, cites real log lines, runs a live local model, and scores itself — on a laptop. No GB10 required for this demo.

## Beat 02 — Live console (0:25–0:45)
Here is the console at localhost 8787. Laptop mode. Model online — Qwen 2.5 7B on Ollama.
Seven live cases. Five golden evals. Eighty real NVIDIA Container Toolkit issues in the corpus — about sixty percent incomplete by the same checklist we enforce.

## Beat 03 — Audit gaps (0:45–1:10)
Open CASE-1042 — serving CUDA out-of-memory. Reset to the incomplete pack.
Run evidence audit. Score about sixty percent. Missing environment dump and nvidia-smi. That is the everyday reality of GPU support tickets.

## Beat 04 — Inject + investigate (1:10–1:50)
Inject the missing evidence. Audit jumps to one hundred percent.
The rule layer already cites CUDA OOM and an abandoned train_scratch process holding memory.
Now investigate with the live model. The LLM report is grounded in files — citations, not vibes. That is the handoff an on-call engineer can trust.

## Beat 05 — Measured quality (1:50–2:20)
Run the live LLM eval across five golden failure families: OOM, Xid seventy-nine, NCCL hang, driver mismatch, and ECC remapped rows.
Judges can reproduce this with one script. We do not ask you to believe a chat transcript — we show pass rate and average score.

## Beat 06 — Security + OpenShell (2:20–2:45)
Ask the agent to run a shell and reset the GPU — denied. Path sandbox, redaction, audit JSONL.
Optional production path: OpenShell and NemoClaw on the same laptop — policy-isolated egress, local inference only. Isolation you can prove.

## Beat 07 — Close (2:45–3:00)
Not a chatbot paste. A checked, scored case package — laptop today, OpenShell when you need policy.
That is SupportForge. Thank you.
