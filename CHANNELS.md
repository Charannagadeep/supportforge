# Messaging channels (optional)

After NemoClaw onboard:

```bash
# Telegram
export TELEGRAM_BOT_TOKEN=...
nemoclaw my-assistant channels add telegram

# Slack (Socket Mode)
export SLACK_BOT_TOKEN=xoxb-...
export SLACK_APP_TOKEN=xapp-...
nemoclaw my-assistant channels add slack
```

Suggested bot message when completeness changes:

> SupportForge · CASE-1042 · completeness 60% → missing environment_manifest, gpu_snapshot · handoff: workspace/outbox/CASE-1042-handoff.md
