# Agents

## Main — SupportForge

Always-on support investigation agent.

### Skills

| Skill | When |
|-------|------|
| `evidence-audit` | New/updated case folder; user asks to audit or triage |
| `timeline-builder` | Enough logs exist to reconstruct failure sequence |
| `escalation-handoff` | Produce or refresh engineering handoff package |

### Paths

- Cases: `workspace/cases/<CASE-ID>/`
- Runbooks: `workspace/runbooks/`
- Handoffs: `workspace/outbox/`
- State: `workspace/memory/`
- Template: `workspace/templates/handoff.md`

### Channels

Slack / Discord / Telegram via NemoClaw (`nemoclaw <sandbox> channels add …`). Prefer posting a short completeness summary + path to the handoff file.

The watcher (`app/watcher.py`) owns the change *trigger* and de-duplication; a channel transport registers itself via `watcher.set_channel_notifier(fn)` and receives a payload (`case_id`, `completeness_percent`, `top_missing`, `handoff_path`, `revision`). Keeping the transport behind this seam lets the channel owner (console/channel workstream) wire Slack/Discord/Telegram without touching the loop.

### Always-on loop

Implemented in `app/watcher.py`, started on app boot when `SUPPORTFORGE_WATCH=1`. It polls `workspace/cases/`, re-audits changed cases, refreshes the handoff narrative (local model when online, rule layer otherwise), appends to `workspace/outbox/WATCH.md`, and stamps `workspace/memory/last-scan.json`. See `HEARTBEAT.md`.
