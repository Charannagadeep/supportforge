"""Deterministic evidence engine for SupportForge (runs fully local, no LLM required)."""
from __future__ import annotations

import json
import re
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .security import allowed_case_path, allowed_output_path, audit_security, find_prompt_injection_markers

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "workspace"
CASES_DIR = WORKSPACE / "cases"
OUTBOX = WORKSPACE / "outbox"
RUNBOOKS = WORKSPACE / "runbooks"
DEMO_COMPLETE = ROOT / "cases"
CASE_ID_RE = re.compile(r"^CASE-[0-9]+$")

REQUIRED = [
    ("problem_statement", ["customer/description.md"]),
    ("environment_manifest", ["incoming/environment.json", "incoming/env.txt"]),
    ("gpu_snapshot", ["incoming/nvidia-smi.txt", "incoming/nvidia_smi.txt"]),
    ("primary_logs", ["incoming/*.log"]),
    ("steps_tried", ["customer/steps-tried.md"]),
]

RECOMMENDED = [
    ("kernel_log", ["incoming/dmesg.txt"]),
    ("driver_notes", ["incoming/driver-version.txt"]),
]

ERROR_RE = re.compile(
    r"ERROR|OutOfMemory|CUDA out of memory|Xid|segfault|FATAL|panic|NVRM",
    re.I,
)


@dataclass
class EvidenceRow:
    item: str
    status: str
    paths: list[str] = field(default_factory=list)
    required: bool = True


@dataclass
class TimelineEvent:
    time: str
    summary: str
    citation: str
    severity: str = "info"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ensure_layout() -> None:
    for p in (CASES_DIR, OUTBOX, RUNBOOKS, WORKSPACE / "memory", WORKSPACE / "templates"):
        p.mkdir(parents=True, exist_ok=True)


def validate_case_id(case_id: str) -> str:
    """Allow only the repository's case identifier format before path joins."""
    if not CASE_ID_RE.fullmatch(case_id or ""):
        raise FileNotFoundError(f"Unknown case: {case_id}")
    return case_id


def list_cases() -> list[dict[str, Any]]:
    ensure_layout()
    cases = []
    for d in sorted(CASES_DIR.iterdir() if CASES_DIR.exists() else []):
        if not d.is_dir() or d.name.startswith("."):
            continue
        audit_path = d / "audit.json"
        audit = json.loads(audit_path.read_text()) if audit_path.exists() else None
        handoff = OUTBOX / f"{d.name}-handoff.md"
        cases.append(
            {
                "id": d.name,
                "path": str(d),
                "completeness": (audit or {}).get("completeness_percent"),
                "updated": (audit or {}).get("updated"),
                "has_handoff": handoff.exists(),
                "files": _file_count(d),
            }
        )
    return cases


def _file_count(case: Path) -> int:
    return sum(1 for p in case.rglob("*") if p.is_file() and p.name != "audit.json")


def resolve_paths(case: Path, patterns: list[str]) -> list[Path]:
    found: list[Path] = []
    case_root = case.resolve()
    for pat in patterns:
        if "*" in pat:
            found.extend(sorted(case.glob(pat)))
        else:
            p = case / pat
            if p.exists():
                found.append(p)
    safe: list[Path] = []
    for p in found:
        resolved = p.resolve()
        if resolved != case_root and case_root not in resolved.parents:
            audit_security("file_access", result="denied", path=str(p.relative_to(case)))
            continue
        if resolved.is_file() and resolved.stat().st_size > 0:
            safe.append(resolved)
    return safe


def score_status(paths: list[Path]) -> str:
    if not paths:
        return "missing"
    if all(p.stat().st_size < 40 for p in paths):
        return "weak"
    return "present"


def audit_case(case_id: str) -> dict[str, Any]:
    ensure_layout()
    case_id = validate_case_id(case_id)
    case = CASES_DIR / case_id
    if not case.is_dir():
        raise FileNotFoundError(f"Unknown case: {case_id}")
    case_root = CASES_DIR.resolve()
    resolved_case = case.resolve()
    if resolved_case != case_root and case_root not in resolved_case.parents:
        raise FileNotFoundError(f"Case is outside approved workspace: {case_id}")

    rows: list[EvidenceRow] = []
    present = 0
    for key, pats in REQUIRED:
        paths = resolve_paths(case, pats)
        st = score_status(paths)
        if st == "present":
            present += 1
        rows.append(
            EvidenceRow(
                item=key,
                status=st,
                paths=[str(p.relative_to(case)) for p in paths],
                required=True,
            )
        )
    for key, pats in RECOMMENDED:
        paths = resolve_paths(case, pats)
        rows.append(
            EvidenceRow(
                item=key,
                status=score_status(paths),
                paths=[str(p.relative_to(case)) for p in paths],
                required=False,
            )
        )

    pct = round(100 * present / len(REQUIRED))
    events = build_timeline(case)
    hypotheses = build_hypotheses(case, rows, events)
    runbook_hits = match_runbooks(case, events)
    security_flags: list[str] = []
    for evidence_file in case.rglob("*"):
        if not evidence_file.is_file() or evidence_file.name in {"audit.json", "timeline.md"}:
            continue
        markers = find_prompt_injection_markers(evidence_file.read_text(errors="replace"))
        if markers:
            security_flags.extend(markers)
    security_flags = sorted(set(security_flags))

    audit = {
        "case_id": case_id,
        "completeness_percent": pct,
        "evidence": [asdict(r) for r in rows],
        "timeline": [asdict(e) for e in events],
        "hypotheses": hypotheses,
        "runbooks": runbook_hits,
        "security_flags": security_flags,
        "updated": _now(),
    }
    (case / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")

    missing = [r for r in rows if r.required and r.status != "present"]
    _write_requests(case_id, pct, missing)
    if events:
        _write_timeline_md(case, events)
    handoff_path = _write_handoff(case, case_id, pct, rows, events, hypotheses, runbook_hits, missing, security_flags)
    audit["handoff_path"] = str(handoff_path)
    audit["requests_path"] = str(OUTBOX / f"{case_id}-requests.md")
    audit_security(
        "case_audit",
        actor="local-engine",
        case_id=case_id,
        completeness=pct,
        security_flags=len(security_flags),
    )
    return audit


def build_timeline(case: Path) -> list[TimelineEvent]:
    events: list[TimelineEvent] = []
    incoming = case / "incoming"
    if not incoming.exists():
        return events
    for log in sorted(incoming.glob("*.log")) + sorted(incoming.glob("dmesg.txt")):
        for i, line in enumerate(log.read_text(errors="replace").splitlines(), 1):
            if not ERROR_RE.search(line) and "loading weights" not in line.lower():
                # keep a few milestones + errors
                if not re.search(r"start version|weights loaded|shutdown", line, re.I):
                    continue
            sev = "error" if ERROR_RE.search(line) else "info"
            parts = line.split(" ", 1)
            ts = parts[0] if parts and ("T" in parts[0] or parts[0][:4].isdigit()) else "unknown"
            events.append(
                TimelineEvent(
                    time=ts,
                    summary=line.strip()[:180],
                    citation=f"{log.relative_to(case)}:{i}",
                    severity=sev,
                )
            )
    # Prefer chronological by timestamp string when ISO-like
    events.sort(key=lambda e: (e.time == "unknown", e.time))
    return events


def build_hypotheses(case: Path, rows: list[EvidenceRow], events: list[TimelineEvent]) -> list[str]:
    hyps: list[str] = []
    case_id = case.name
    log_text = ""
    for r in rows:
        if r.item == "primary_logs":
            for rel in r.paths:
                try:
                    log_text += allowed_case_path(case_id, rel).read_text(errors="replace")
                except ValueError:
                    audit_security("file_access", result="denied", path=rel, case_id=case_id)
    smi_text = ""
    for r in rows:
        if r.item == "gpu_snapshot" and r.paths:
            try:
                smi_text = allowed_case_path(case_id, r.paths[0]).read_text(errors="replace")
            except ValueError:
                audit_security("file_access", result="denied", path=r.paths[0], case_id=case_id)

    if "CUDA out of memory" in log_text or "OutOfMemoryError" in log_text:
        hyps.append(
            "GPU memory exhaustion during serving init — supported by CUDA OOM lines in serving logs."
        )
    if "train_scratch" in smi_text:
        hyps.append(
            "Competing abandoned process `train_scratch.py` is holding majority of GPU memory — supported by nvidia-smi process table."
        )
    if re.search(r"Xid|NVRM: Xid", log_text + smi_text, re.I):
        hyps.append(
            "Possible GPU/driver fault (Xid) — supported by kernel/driver log markers; collect full dmesg before RMA assumptions."
        )
    if not hyps and any(e.severity == "error" for e in events):
        hyps.append(
            "Application error observed in logs — environment/GPU snapshot still needed before root-cause lock."
        )
    if not hyps:
        hyps.append("Insufficient evidence for a ranked technical hypothesis.")
    return hyps


def match_runbooks(case: Path, events: list[TimelineEvent]) -> list[dict[str, str]]:
    hits = []
    blob = " ".join(e.summary for e in events).lower()
    mapping = [
        ("cuda-oom-serving.md", ["cuda out of memory", "outofmemory"]),
        ("xid-driver.md", ["xid", "nvrm"]),
    ]
    for name, keys in mapping:
        path = RUNBOOKS / name
        if path.exists() and any(k in blob for k in keys):
            hits.append({"name": name, "path": str(path.relative_to(ROOT))})
    return hits


def _write_requests(case_id: str, pct: int, missing: list[EvidenceRow]) -> Path:
    lines = [f"# Customer requests — {case_id}", "", f"Completeness: **{pct}%**", ""]
    if missing:
        lines.append("Please provide the following before engineering can investigate effectively:")
        labels = {
            "environment_manifest": "Environment manifest (OS, GPU, driver, CUDA, framework, serving config) as `environment.json`",
            "gpu_snapshot": "`nvidia-smi` text capture near the failure (`nvidia-smi.txt`)",
            "primary_logs": "Application / serving logs covering the failure window",
            "problem_statement": "Clear problem statement with impact and timing",
            "steps_tried": "Steps already attempted",
        }
        for r in missing:
            lines.append(f"- **{r.item}**: {labels.get(r.item, r.item)}")
    else:
        lines.append("All required evidence is present. No blocking customer asks.")
    path = allowed_output_path(case_id, "requests.md")
    path.write_text("\n".join(lines) + "\n")
    return path


def _write_timeline_md(case: Path, events: list[TimelineEvent]) -> Path:
    lines = [f"# Timeline — {case.name}", ""]
    for e in events:
        mark = "🔴" if e.severity == "error" else "•"
        lines.append(f"- {mark} **{e.time}** — {e.summary}")
        lines.append(f"  - cite: `{e.citation}`")
    path = allowed_case_path(case.name, "timeline.md")
    path.write_text("\n".join(lines) + "\n")
    return path


def _write_handoff(
    case: Path,
    case_id: str,
    pct: int,
    rows: list[EvidenceRow],
    events: list[TimelineEvent],
    hypotheses: list[str],
    runbooks: list[dict[str, str]],
    missing: list[EvidenceRow],
    security_flags: list[str],
) -> Path:
    desc = ""
    try:
        desc_path = allowed_case_path(case_id, "customer/description.md")
        if desc_path.exists():
            desc = desc_path.read_text(errors="replace").strip().splitlines()
            desc = " ".join(l for l in desc if l and not l.startswith("#"))[:280]
    except ValueError:
        pass

    env_block = "_Unknown — environment manifest missing._"
    for r in rows:
        if r.item == "environment_manifest" and r.paths:
            try:
                raw = allowed_case_path(case_id, r.paths[0]).read_text(errors="replace")
                env_block = f"```\n{raw.strip()[:2000]}\n```"
            except ValueError:
                audit_security("file_access", result="denied", path=r.paths[0], case_id=case_id)

    table = "\n".join(
        f"| {r.item} | {r.status} | {', '.join(r.paths) or '—'} | {'yes' if r.required else 'no'} |"
        for r in rows
    )
    tl = "\n".join(f"- **{e.time}** — {e.summary} (`{e.citation}`)" for e in events) or "_No timeline events extracted._"
    hy = "\n".join(f"{i}. {h}" for i, h in enumerate(hypotheses, 1))
    rb = "\n".join(f"- `{r['name']}`" for r in runbooks) or "_No runbook auto-match._"
    unk = "\n".join(f"- Missing/weak required: `{r.item}`" for r in missing) or "- None for required set"
    next_checks = [
        "1. If nvidia-smi shows non-serving GPU processes, confirm owner and stop abandoned jobs before resizing models.",
        "2. Re-run serving after memory is free; record gpu_memory_utilization / max_model_len / max_num_seqs.",
        "3. If OOM clears but crash persists, capture dmesg + driver versions and re-open with Xid focus.",
    ]

    body = f"""# Engineering handoff — {case_id}

**Generated by:** SupportForge (local evidence engine)  
**Updated:** {_now()}  
**Completeness:** {pct}%  
**Mode:** laptop-local (swap to GB10 vLLM without changing this package format)

## Summary

{desc or 'Support case packaged for engineering review.'} Completeness is **{pct}%**.

## Completeness

| Item | Status | Path | Required |
|------|--------|------|----------|
{table}

## Environment

{env_block}

## Timeline (cited)

{tl}

## Observations

- Required evidence completeness: **{pct}%**
- Error/milestone events extracted: **{len(events)}**
- Matched runbooks: {len(runbooks)}
- Security review: {len(security_flags)} instruction-like marker(s) detected; evidence content was treated as untrusted data.

## Hypotheses (ranked, rule layer)

{hy}

## Matched runbooks

{rb}

## Unknowns

{unk}

## Next checks

{chr(10).join(next_checks)}

## Customer requests (blocking)

See `{case_id}-requests.md` in outbox.

## How to reproduce locally

```bash
# laptop
curl -s -X POST http://127.0.0.1:8787/api/cases/{case_id}/investigate | jq .
# GB10 (OpenAI-compatible vLLM on :8000 auto-detected)
SUPPORTFORGE_LLM_BASE=http://127.0.0.1:8000/v1 SUPPORTFORGE_MODEL=<served-model> \\
  curl -s -X POST http://127.0.0.1:8787/api/cases/{case_id}/investigate | jq .
```

---
*Private case data — processed locally. Live model narrative appends below when Investigate runs.*
"""
    path = allowed_output_path(case_id, "handoff.md")
    path.write_text(body)
    return path


def read_outbox_file(case_id: str, kind: str) -> str:
    case_id = validate_case_id(case_id)
    if kind not in {"handoff", "requests"}:
        raise FileNotFoundError(kind)
    try:
        path = allowed_output_path(case_id, f"{kind}.md")
    except ValueError as e:
        raise FileNotFoundError(str(e)) from e
    if not path.exists():
        raise FileNotFoundError(path.name)
    return path.read_text()


def reset_demo_case(case_id: str = "CASE-1042") -> dict[str, Any]:
    """Reset live case to incomplete pack for demo."""
    ensure_layout()
    case_id = validate_case_id(case_id)
    src = DEMO_COMPLETE / case_id
    if not src.exists():
        raise FileNotFoundError(src)
    dest = CASES_DIR / case_id
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)
    # wipe prior outbox artifacts for this case
    for p in OUTBOX.glob(f"{case_id}-*"):
        p.unlink()
    return audit_case(case_id)


def inject_complete_evidence(case_id: str = "CASE-1042") -> dict[str, Any]:
    """Copy missing evidence from *-complete pack into live case (demo step 2)."""
    ensure_layout()
    case_id = validate_case_id(case_id)
    complete = DEMO_COMPLETE / f"{case_id}-complete"
    if not complete.exists():
        # fallback naming
        complete = DEMO_COMPLETE / f"{case_id}_complete"
    if not complete.exists():
        raise FileNotFoundError(f"No complete pack for {case_id}")
    dest = CASES_DIR / case_id
    dest.mkdir(parents=True, exist_ok=True)
    for src in (complete / "incoming").glob("*"):
        target = dest / "incoming" / src.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
    for src in (complete / "customer").glob("*"):
        target = dest / "customer" / src.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
    return audit_case(case_id)


def seed_all_demo_cases() -> list[str]:
    ensure_layout()
    seeded = []
    for src in DEMO_COMPLETE.iterdir():
        if not src.is_dir() or src.name.endswith("-complete"):
            continue
        dest = CASES_DIR / src.name
        if not dest.exists():
            shutil.copytree(src, dest)
            seeded.append(src.name)
            audit_case(src.name)
    return seeded
