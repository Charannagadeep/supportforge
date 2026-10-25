---
name: timeline-builder
description: Build a failure timeline from case logs with citations to real timestamps and file paths. Never invent log lines.
---

# Timeline builder

## When to run

After evidence-audit, when at least one log file exists under `workspace/cases/<ID>/incoming/`.

## Procedure

1. Read available logs (`*.log`, `dmesg.txt`, etc.).
2. Extract events with timestamps (or file order if no timestamps — mark as **unordered**).
3. Build a chronological list. Each row must include:
   - time (or `unknown`)
   - event summary (one line)
   - **citation**: `path:line` or quoted snippet ≤120 chars from the file
4. Mark the likely **failure moment** (crash, OOM, CUDA error, segfault).
5. Write `workspace/cases/<ID>/timeline.md`.

## Rules

- If you cannot find a line in the file, do not include the event.
- Prefer CUDA / driver / OOM / traceback markers.
- Separate **customer-reported** symptoms from **log-observed** facts.
