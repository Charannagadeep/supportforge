#!/usr/bin/env python3
"""Speed-fit cloned voice to target length + burn subs onto website recording (no loop)."""
from __future__ import annotations

import re
import shutil
import subprocess
import wave
from pathlib import Path

import imageio_ffmpeg

ROOT = Path(__file__).resolve().parent
CLONED = ROOT / "audio" / "narration_cloned.wav"
SYNC = ROOT / "audio" / "narration_synced.wav"
SRT = ROOT / "audio" / "narration_synced.srt"
ASS = ROOT / "audio" / "narration_synced.ass"
NARRATION = (ROOT / "narration.txt").read_text().strip()
VIDEO_IN = ROOT / "raw" / "website-demo.webm"
VIDEO_OUT = ROOT / "SupportForge-Website-Demo.mp4"
DESK = Path.home() / "Desktop" / "SupportForge-Website-Demo.mp4"
JUDGE = ROOT.parent / "SupportForge-Judge-Demo.mp4"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
TARGET_SEC = 175.0

# Beat-aligned sections (must match record_demo.py SECTIONS order)
SECTION_TEXTS = [
    (
        "Welcome, judges. This is SupportForge — our local evidence laboratory for enterprise GPU and AI-server support on Dell GB10. "
        "Cases arrive incomplete. Engineers cannot start until environment, nvidia-smi, logs, and a failure timeline exist. "
        "You are looking at the live SupportForge website. Status is GB10 pack online. "
        "The USB drive carries Qwen 3.6 35B NVFP4 and Nemotron Nano 4B — both verified and ready for vLLM on the box. "
        "We show seven live cases, five golden evals, and eighty real NVIDIA Container Toolkit issues. "
        "About sixty percent of those real issues are incomplete by the same checklist we enforce. That proves the problem is not synthetic."
    ),
    (
        "Let us walk the product. Open CASE-1042 — a serving CUDA out-of-memory failure on a GB10 lab node. "
        "I reset it to the incomplete pack — exactly how tickets usually arrive from the field."
    ),
    (
        "Now run evidence audit. Completeness is about sixty percent. The environment dump is missing. "
        "The nvidia-smi snapshot is missing. Serving logs and customer notes are present. "
        "This is the everyday gap that blocks on-call engineers before they can even begin."
    ),
    (
        "Next, inject the missing evidence. Watch completeness jump to one hundred percent. "
        "The rule layer already cites CUDA out of memory in the serving log, and an abandoned train_scratch process holding GPU memory in nvidia-smi."
    ),
    (
        "Now press Investigate. SupportForge calls the live local model and writes a cited investigation report — "
        "grounded in the case files, with filenames and log-backed hypotheses. Not a chatbot guess. A handoff an engineer can trust."
    ),
    (
        "Open the LLM report tab. Here is the live narrative: summary, completeness, ranked hypotheses, unknowns, and next checks — all tied back to evidence."
    ),
    (
        "We also score ourselves. Run the eval harness across five golden failure families: OOM, Xid seventy-nine, NCCL hang, driver mismatch, and ECC remapped rows. "
        "The eval board shows pass rate and average score. Judges can reproduce this with one script. We do not ask you to believe a chat transcript."
    ),
    (
        "Security is part of the product. Ask the agent to run a shell and reset the GPU. It is denied. "
        "Path sandbox, restricted tools, redaction, and an audit trail. Private case data stays local."
    ),
    (
        "Finally, open the NVIDIA corpus tab. Eighty real toolkit issues — incomplete reports still show meaningful evidence percentages, not empty zeros. "
        "The gap pattern matches what SupportForge audits in every demo case. "
        "SupportForge is not a chatbot paste. It is a checked, scored case package — USB models loaded for Dell GB10, stronger with OpenShell isolation on the box. Thank you, judges."
    ),
]


def wav_dur(path: Path) -> float:
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / float(w.getframerate())


def ts(sec: float) -> str:
    if sec < 0:
        sec = 0
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    ms = int(round((sec - int(sec)) * 1000))
    if ms == 1000:
        s += 1
        ms = 0
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def wrap(text: str, max_chars: int = 28) -> str:
    """One short line preferred; hard cap two short lines."""
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if len(trial) <= max_chars:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    lines = lines[:2]
    return "\n".join(lines)


def short_phrases(text: str, max_words: int = 6) -> list[str]:
    """Break a sentence into short subtitle cards."""
    text = re.sub(r"[—–]", " - ", text)
    parts = [p.strip() for p in re.split(r"\s*[,;:]\s*|\s+-\s+", text) if p.strip()]
    if not parts:
        parts = [text]
    out: list[str] = []
    for part in parts:
        words = part.split()
        if len(words) <= max_words:
            out.append(" ".join(words))
            continue
        for i in range(0, len(words), max_words):
            chunk = " ".join(words[i : i + max_words]).strip(" .")
            if chunk:
                out.append(chunk)
    # Merge tiny fragments so we don't flash single words
    cleaned: list[str] = []
    for p in out:
        words = p.split()
        if cleaned and (
            len(words) <= 2
            or (len(words) <= 3 and len(cleaned[-1].split()) <= 4)
        ):
            cleaned[-1] = (cleaned[-1] + " " + p).strip()
        else:
            cleaned.append(p)
    return cleaned or [text]


def fit_audio() -> float:
    src = wav_dur(CLONED)
    factor = src / TARGET_SEC
    print(f"cloned={src:.1f}s → target={TARGET_SEC:.1f}s atempo={factor:.3f}")
    filters = []
    f = factor
    while f > 2.0:
        filters.append("atempo=2.0")
        f /= 2.0
    while f < 0.5:
        filters.append("atempo=0.5")
        f /= 0.5
    filters.append(f"atempo={f:.4f}")
    r = subprocess.run(
        [
            FFMPEG,
            "-y",
            "-i",
            str(CLONED),
            "-af",
            ",".join(filters),
            "-ar",
            "44100",
            "-ac",
            "1",
            str(SYNC),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if r.returncode != 0:
        print(r.stderr[-2000:])
        raise SystemExit("atempo failed")
    dur = wav_dur(SYNC)
    print(f"synced_audio={dur:.2f}s")
    return dur


def ass_time(sec: float) -> str:
    if sec < 0:
        sec = 0
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    cs = int(round((sec - int(sec)) * 100))
    if cs == 100:
        s += 1
        cs = 0
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def write_srt(dur: float) -> None:
    weights = [len(t) for t in SECTION_TEXTS]
    total = sum(weights) or 1
    cues: list[tuple[float, float, str]] = []
    t = 0.0
    for text, w in zip(SECTION_TEXTS, weights):
        span = (w / total) * dur
        phrases: list[str] = []
        for s in [x.strip() for x in re.split(r"(?<=[.!?])\s+", text) if x.strip()]:
            phrases.extend(short_phrases(s, max_words=6))
        weights_p = [max(1, len(p.split())) for p in phrases]
        pw = sum(weights_p) or 1
        local = t
        for p, pw_i in zip(phrases, weights_p):
            sspan = max(0.55, (pw_i / pw) * span)
            end = min(t + span, local + sspan)
            cues.append((local, end, p))
            local = end
        if cues:
            a, _, tx = cues[-1]
            cues[-1] = (a, t + span, tx)
        t += span
    if cues:
        a, _, tx = cues[-1]
        cues[-1] = (a, dur, tx)
    lines = []
    for i, (a, b, text) in enumerate(cues, 1):
        lines += [str(i), f"{ts(a)} --> {ts(b)}", wrap(text), ""]
    SRT.write_text("\n".join(lines), encoding="utf-8")

    # ASS with PlayRes 1080p — Alignment 2 + tiny MarginV pins captions to the bottom edge
    ass_lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1920",
        "PlayResY: 1080",
        "WrapStyle: 0",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding",
        # Captions sit in the bottom letterbox bar (see mux pad); MarginV keeps them in that strip
        "Style: Default,Arial,16,&H00FFFFFF,&H000000FF,&HC0000000,&HC0000000,"
        "0,0,0,0,100,100,0,0,3,1.0,0,2,80,80,18,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    for a, b, text in cues:
        body = wrap(text).replace("\n", r"\N")
        ass_lines.append(
            f"Dialogue: 0,{ass_time(a)},{ass_time(b)},Default,,0,0,0,,{body}"
        )
    ASS.write_text("\n".join(ass_lines) + "\n", encoding="utf-8")
    print(f"srt_cues={len(cues)} ass={ASS.name}")


def print_section_budget(dur: float) -> dict[str, float]:
    weights = [len(t) for t in SECTION_TEXTS]
    total = sum(weights) or 1
    names = [
        "welcome",
        "reset",
        "audit",
        "inject",
        "investigate",
        "llm",
        "eval",
        "security",
        "close",
    ]
    budget = {name: round((w / total) * dur, 1) for name, w in zip(names, weights)}
    print("section_budget_sec = {")
    for name, sec in budget.items():
        print(f'    "{name}": {sec},')
    print("}")
    return budget


def mux(audio_dur: float) -> None:
    if not VIDEO_IN.exists():
        raise SystemExit(f"missing {VIDEO_IN}")
    vprobe = subprocess.run([FFMPEG, "-i", str(VIDEO_IN)], stderr=subprocess.PIPE, text=True)
    for line in vprobe.stderr.splitlines():
        if "Duration" in line:
            part = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = part.split(":")
            vdur = int(h) * 3600 + int(m) * 60 + float(s)
            print(f"video={vdur:.2f}s audio={audio_dur:.2f}s")
            break

    ass_esc = str(ASS.resolve()).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
    # Fit UI into top 1000px, pad black 80px caption bar at bottom so subs never cover the product
    vf = (
        f"scale=1920:1000:force_original_aspect_ratio=decrease,"
        f"pad=1920:1080:(ow-iw)/2:0:black,setsar=1,fps=30,"
        f"ass={ass_esc}"
    )
    cmd = [
        FFMPEG,
        "-y",
        "-i",
        str(VIDEO_IN),
        "-i",
        str(SYNC),
        "-vf",
        vf,
        "-map",
        "0:v",
        "-map",
        "1:a",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        "-movflags",
        "+faststart",
        str(VIDEO_OUT),
    ]
    print("muxing…")
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if r.returncode != 0:
        print(r.stderr[-2500:])
        raise SystemExit("mux failed")
    shutil.copy2(VIDEO_OUT, DESK)
    shutil.copy2(VIDEO_OUT, JUDGE)
    probe = subprocess.run([FFMPEG, "-i", str(VIDEO_OUT)], stderr=subprocess.PIPE, text=True)
    for line in probe.stderr.splitlines():
        if "Duration" in line or "Video:" in line or "Audio:" in line:
            print(line.strip())
    print("DESKTOP", DESK)


def main():
    dur = fit_audio()
    write_srt(dur)
    print_section_budget(dur)
    mux(dur)


if __name__ == "__main__":
    main()
