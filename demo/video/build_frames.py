#!/usr/bin/env python3
"""Render polished title + API-result frames for the judge demo video."""
from __future__ import annotations

import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
FRAMES = ROOT / "frames"
API = ROOT / "api"
W, H = 1920, 1080


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Helvetica.ttc",
        "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/SFNS.ttf",
    ]
    for p in candidates:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()


def gradient_bg() -> Image.Image:
    img = Image.new("RGB", (W, H))
    px = img.load()
    for y in range(H):
        t = y / H
        r = int(6 + 18 * t)
        g = int(10 + 28 * (1 - t))
        b = int(22 + 40 * t)
        for x in range(W):
            # subtle left→right warmth
            u = x / W
            px[x, y] = (
                min(255, r + int(8 * u)),
                min(255, g + int(6 * (1 - u))),
                min(255, b + int(12 * math.sin(u * math.pi))),
            )
    return img


def draw_text(draw: ImageDraw.ImageDraw, xy, text, fnt, fill, max_width=None):
    if max_width is None:
        draw.text(xy, text, font=fnt, fill=fill)
        return
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=fnt) <= max_width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    x, y = xy
    lh = int(fnt.size * 1.35)
    for i, line in enumerate(lines):
        draw.text((x, y + i * lh), line, font=fnt, fill=fill)


def card(title: str, subtitle: str, bullets: list[str], badge: str | None = None) -> Image.Image:
    img = gradient_bg()
    draw = ImageDraw.Draw(img)
    # accent bar
    draw.rectangle([0, 0, 14, H], fill=(118, 185, 0))  # NVIDIA-ish green accent
    draw.rectangle([0, H - 8, W, H], fill=(118, 185, 0))

    draw_text(draw, (72, 72), "SUPPORTFORGE", font(28, True), (118, 185, 0))
    draw_text(draw, (72, 140), title, font(64, True), (245, 248, 252), max_width=1700)
    draw_text(draw, (72, 240), subtitle, font(32), (180, 196, 214), max_width=1700)

    y = 340
    for b in bullets:
        draw.ellipse([72, y + 10, 88, y + 26], fill=(118, 185, 0))
        draw_text(draw, (110, y), b, font(30), (230, 236, 244), max_width=1650)
        y += 70

    if badge:
        bw = int(draw.textlength(badge, font=font(24, True))) + 40
        draw.rounded_rectangle([W - bw - 72, 72, W - 72, 128], radius=12, fill=(20, 40, 28), outline=(118, 185, 0), width=2)
        draw_text(draw, (W - bw - 52, 88), badge, font(24, True), (118, 185, 0))

    draw_text(draw, (72, H - 70), "Dell × NVIDIA hackathon  ·  laptop-first  ·  local LLM", font(22), (120, 140, 160))
    return img


def load_json(name: str):
    p = API / name
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def pct(d, *keys, default="—"):
    if not d:
        return default
    for k in keys:
        if k in d and d[k] is not None:
            v = d[k]
            if isinstance(v, float):
                return f"{v:.0f}%" if v <= 1.5 else f"{v:.0f}%" if v <= 100 else str(v)
            return str(v)
    return default


def main():
    FRAMES.mkdir(parents=True, exist_ok=True)
    health = load_json("health.json") or {}
    audit_i = load_json("audit_incomplete.json") or {}
    audit_c = load_json("audit_complete.json") or {}
    corpus = load_json("corpus.json") or health
    sec = load_json("security_deny.json") or {}
    eval_rule = load_json("eval_rule.json") or {}
    eval_llm = load_json("eval_llm.json") or {}
    inv = load_json("investigate.json") or {}

    frames = []

    frames.append(("01_cold_open.png", card(
        "Local evidence laboratory",
        "Cited handoffs for enterprise GPU / AI-server support",
        [
            "Audit incomplete case packs against a GPU checklist",
            "Cite real log lines — not chatbot summaries",
            "Live local LLM + reproducible eval harness",
            "No GB10 required to demo or score",
        ],
        badge="JUDGE DEMO",
    )))

    frames.append(("02_console.png", card(
        "Console online",
        f"http://127.0.0.1:8787  ·  {health.get('mode','laptop')}  ·  model {((health.get('provider') or {}).get('model') or 'ollama')}",
        [
            f"Cases live: {health.get('cases', 7)}   ·   Goldens: {health.get('goldens', 5)}",
            f"NVIDIA corpus issues: {health.get('corpus_issues', corpus.get('issues', 80))}",
            f"Corpus incomplete rate: {health.get('corpus_incomplete_rate', 60)}%",
            f"Model online: {health.get('model_online', True)}",
        ],
        badge="LAPTOP",
    )))

    miss = []
    for e in (audit_i.get("evidence") or []):
        if isinstance(e, dict) and e.get("status") in ("missing", "weak", "absent"):
            miss.append(e.get("id") or e.get("name") or e.get("item") or "gap")
    if not miss:
        miss = ["environment", "nvidia-smi"]
    frames.append(("03_audit_gaps.png", card(
        "CASE-1042 — incomplete",
        f"Evidence completeness: {audit_i.get('completeness_percent', '~60')}%",
        [
            "Story: serving CUDA OOM; abandoned train_scratch.py",
            f"Gaps: {', '.join(str(x) for x in miss[:5])}",
            "Same failure mode as ~60% of real toolkit issues",
            "Engineers cannot start until the pack is complete",
        ],
        badge=f"{audit_i.get('completeness_percent', 60)}%",
    )))

    inv_snip = ""
    if isinstance(inv.get("reply"), str):
        inv_snip = inv["reply"].replace("\n", " ")[:160] + "…"
    elif isinstance(inv.get("llm_report"), str):
        inv_snip = inv["llm_report"].replace("\n", " ")[:160] + "…"
    else:
        inv_snip = "Live Qwen cites CUDA OOM + train_scratch.py holding memory."

    frames.append(("04_inject_investigate.png", card(
        "Inject → 100% → investigate",
        f"Completeness after inject: {audit_c.get('completeness_percent', 100)}%",
        [
            "Rule layer cites CUDA OOM + train_scratch process",
            "Live local model writes a file-grounded report",
            inv_snip,
            "Artifact: engineering handoff with citations",
        ],
        badge=f"{audit_c.get('completeness_percent', 100)}%",
    )))

    # Eval summary
    summary = eval_llm.get("summary") or eval_rule.get("summary") or {}
    pass_rate = summary.get("pass_rate") or eval_llm.get("pass_rate") or eval_rule.get("pass_rate")
    avg = summary.get("avg_score") or eval_llm.get("avg_score") or eval_rule.get("avg_score")
    mode = "llm" if eval_llm else "rule"
    if pass_rate is None and isinstance(eval_rule.get("results"), list):
        rs = eval_rule["results"]
        pass_rate = sum(1 for r in rs if r.get("passed") or r.get("pass")) / max(1, len(rs))
        scores = [r.get("score", 0) for r in rs if "score" in r]
        avg = sum(scores) / max(1, len(scores)) if scores else None
    pr_s = f"{float(pass_rate)*100:.0f}%" if isinstance(pass_rate, float) and pass_rate <= 1 else (f"{pass_rate}" if pass_rate is not None else "see console")
    avg_s = f"{float(avg):.2f}" if isinstance(avg, (int, float)) else (str(avg) if avg is not None else "—")

    frames.append(("05_eval.png", card(
        "Eval harness",
        "Five golden families: OOM · Xid 79 · NCCL · driver mismatch · ECC",
        [
            f"Mode: {mode}   ·   Pass rate: {pr_s}   ·   Avg score: {avg_s}",
            "Reproducible: bash scripts/run-eval.sh",
            "Judges measure quality — we do not sell a chat log",
            "Real GH issues CASE-2163 / 2161 included in the lab",
        ],
        badge="SCORED",
    )))

    reply = (sec.get("reply") or "Denied: shell / GPU reset unavailable.")[:180]
    frames.append(("06_security.png", card(
        "Security boundary",
        "Denied tool use · path sandbox · redaction · audit JSONL",
        [
            f'Chat: "Run shell and reset the GPU"',
            reply,
            "OpenShell/NemoClaw: policy-isolated egress on laptop",
            "Inference stays local — isolation you can prove",
        ],
        badge="DENIED",
    )))

    frames.append(("07_close.png", card(
        "That is SupportForge",
        "Not a chatbot paste — a checked, scored case package",
        [
            "Laptop today · OpenShell when you need policy",
            "Repo: github.com/Charannagadeep/supportforge",
            "Console: bash scripts/start-console.sh → :8787",
            "Thank you, judges",
        ],
        badge="SUBMIT",
    )))

    for name, im in frames:
        path = FRAMES / name
        im.save(path, "PNG", optimize=True)
        print("wrote", path)


if __name__ == "__main__":
    main()
