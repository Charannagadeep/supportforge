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
