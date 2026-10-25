# Required evidence — GPU / model-serving incidents

Aligned with common NVIDIA GPU triage asks and Dell-style support-bundle expectations. Adapt per product; do not invent fields.

## Required

1. **Problem statement** — what failed, when, impact (`customer/description.md`)
2. **Environment manifest** — OS, GPU model, driver, CUDA, framework, serving stack (`incoming/environment.json` or `env.txt`)
3. **GPU snapshot** — `nvidia-smi` text capture (`incoming/nvidia-smi.txt`)
4. **Primary logs** — app / vLLM / Triton / container logs covering the failure window (`incoming/*.log`)
5. **Steps already tried** — restarts, rollbacks, config changes (`customer/steps-tried.md`)

## Strongly recommended

- `incoming/dmesg.txt` or kernel OOM / Xid excerpts
- Driver / fabric manager version notes
- Minimal reproduction (model name, batch size, command)

## Completeness formula

`present_required / total_required * 100` (recommended items do not count against %).
