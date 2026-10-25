---
name: evidence-audit
description: Audit a support case folder for required NVIDIA/Dell-style triage evidence. Lists present, missing, and weak items with file paths.
---

# Evidence audit

## Input

Case id (e.g. `CASE-1042`) or path under `workspace/cases/`.

## Required evidence checklist

Load `workspace/runbooks/required-evidence.md` and score each item:

| Status | Meaning |
|--------|---------|
| **present** | File exists and is non-empty |
| **weak** | File exists but too short / wrong format / no timestamps |
| **missing** | Not found |

### Typical required set (GPU / model-serving crash)

1. Customer problem statement (`customer/description.md`)
2. Environment manifest (`incoming/environment.json` or `incoming/env.txt`)
3. GPU snapshot (`incoming/nvidia-smi.txt`)
4. Primary application / serving logs (`incoming/*.log`)
5. Steps already tried (`customer/steps-tried.md`)
6. Optional but valuable: `incoming/dmesg.txt`, `incoming/driver-version.txt`, minimal repro notes

## Procedure

1. List all files under the case directory recursively.
2. Map files to checklist items (be flexible on names: `nvidia_smi.txt` counts).
3. Compute **completeness %** = present / required (ignore optional for %).
4. Write `workspace/cases/<ID>/audit.json` with statuses and paths.
5. Write `workspace/outbox/<ID>-requests.md` listing missing/weak items as customer asks (one ask per bullet).

## Output to user

- Completeness %
- Table: item → status → path
- Top 1–3 blocking asks
- Do **not** invent missing content
