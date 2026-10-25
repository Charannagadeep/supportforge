# Real NVIDIA evidence corpus

`nvidia_container_toolkit_issues.csv` — cleaned GitHub issues from
[NVIDIA/nvidia-container-toolkit](https://github.com/NVIDIA/nvidia-container-toolkit)
with per-field evidence flags (`has_nvidia_smi_output`, `evidence_pct`, `missing_evidence`, …).

## Why it is in SupportForge

Real support traffic is incomplete. In this corpus:

- average evidence ≈ **52%**
- **~60%** of issues are under 70% evidence
- top gaps: `cuda_version`, `nvidia_smi_output`, `driver_version`, `gpu_model` — the same fields SupportForge audits

Live cases **CASE-2163** and **CASE-2161** are imported from real issues `#2163` and `#2161`.

API: `/api/corpus/stats`, `/api/corpus/issues`, `/api/corpus/issues/{n}`
