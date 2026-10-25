# SupportForge security model

Application-level controls for the Dell × NVIDIA hackathon demo.  
**These do not replace OpenShell / NemoClaw infrastructure policy** (filesystem, egress, process, secrets, messaging).

## Checklist (implemented)

| # | Control | Status |
|---|---------|--------|
| 1 | API key auth (`X-API-Key` / loopback exception) | ✅ |
| 2 | Trusted hosts (`SUPPORTFORGE_ALLOWED_HOSTS`) | ✅ |
| 3 | Bind `127.0.0.1` by default | ✅ |
| 4 | Security response headers | ✅ |
| 5 | 1 MiB request body limit | ✅ |
| 6 | Per-client API rate limit (120/min) | ✅ |
| 7 | Case ID + path sandbox (`CASE-<digits>`) | ✅ |
| 8 | Approved evidence folders only | ✅ |
| 9 | Restricted agent tools / destructive denials | ✅ |
| 10 | Prompt-injection flags + untrusted evidence prompt | ✅ |
| 11 | Secret redaction before model I/O | ✅ |
| 12 | External model assist opt-in only | ✅ |
| 13 | Optional user allowlist | ✅ |
| 14 | Channel allowlist helper (for future connectors) | ✅ |
| 15 | Security audit JSONL (metadata only) | ✅ |
| 16 | UI HTML escaping (`esc()`) | ✅ |
| 17 | CORS disabled unless configured | ✅ |
| 18 | OpenShell/NemoClaw still required for infra | ✅ documented |

## Quick config

```bash
# Laptop demo (default) — no key needed on loopback
bash scripts/start-console.sh

# Shared / GB10
export SUPPORTFORGE_API_KEY='long-random-secret'
export SUPPORTFORGE_ALLOWED_HOSTS='gb10.example.internal,127.0.0.1'
export SUPPORTFORGE_HOST='0.0.0.0'
export SUPPORTFORGE_ALLOWED_USERS='shivanisam,Charannagadeep'
export SUPPORTFORGE_ALLOWED_CHANNELS='supportforge-prod,engineering'
# Optional Anthropic (off by default):
# export SUPPORTFORGE_ALLOW_EXTERNAL_ASSIST=1
# export SUPPORTFORGE_ALLOWED_EXTERNAL_HOSTS='api.anthropic.com'
bash scripts/start-console.sh
```

Browser (when API key is set):

```js
localStorage.setItem("supportforge_api_key", "long-random-secret");
localStorage.setItem("supportforge_user", "shivanisam");
```

## Verify locally

```bash
bash scripts/verify-security.sh
```

Audit trail: `workspace/memory/security-audit.jsonl`
