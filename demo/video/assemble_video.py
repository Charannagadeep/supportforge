#!/usr/bin/env python3
"""Assemble SupportForge judge demo MP4: title cards + live UI + voiceover."""
from __future__ import annotations

import json
import shutil
import subprocess
import wave
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

ROOT = Path(__file__).resolve().parent
FRAMES = ROOT / "frames"
AUDIO = ROOT / "audio"
BUILD = ROOT / "build"
OUT = ROOT / "SupportForge-Judge-Demo.mp4"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
W, H = 1920, 1080
SHOT_DIRS = [
    Path("/var/folders/50/tq9_wxyd2k5fh14z7bpsjkd40000gn/T/cursor/screenshots"),
    FRAMES,
]


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / float(w.getframerate())


def find_shot(name: str) -> Path | None:
    for d in SHOT_DIRS:
        for p in [
            d / name,
            d / f"Users/charan/Desktop/Nvidia/project/demo/video/frames/{name}",
        ]:
            if p.exists():
                return p
        # recursive basename search (shallow)
        if d.exists():
            for p in d.rglob(name):
                return p
    return None


def font(size: int, bold: bool = False):
    for p in (
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Helvetica.ttc",
    ):
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            pass
    return ImageFont.load_default()


def fit_ui(shot: Path, caption: str) -> Image.Image:
    """Place live UI screenshot on dark canvas with caption bar."""
    canvas = Image.new("RGB", (W, H), (8, 12, 18))
    ui = Image.open(shot).convert("RGB")
    # scale to fit with margins
    margin_x, top, bottom = 80, 90, 110
    max_w, max_h = W - 2 * margin_x, H - top - bottom
    scale = min(max_w / ui.width, max_h / ui.height)
    nw, nh = int(ui.width * scale), int(ui.height * scale)
    ui = ui.resize((nw, nh), Image.Resampling.LANCZOS)
    # slight vignette polish
    ui = ImageEnhance.Contrast(ui).enhance(1.05)
    x = (W - nw) // 2
    y = top + (max_h - nh) // 2
    canvas.paste(ui, (x, y))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([0, 0, 14, H], fill=(118, 185, 0))
    draw.rectangle([0, H - 72, W, H], fill=(12, 18, 26))
    draw.text((72, H - 52), caption, font=font(26, True), fill=(118, 185, 0))
    draw.text((72, 28), "SUPPORTFORGE  ·  LIVE UI", font=font(22, True), fill=(118, 185, 0))
    return canvas


def crossfade_pair(a: Image.Image, b: Image.Image, n: int = 12) -> list[Image.Image]:
    out = []
    for i in range(1, n + 1):
        t = i / (n + 1)
        out.append(Image.blend(a, b, t))
    return out


def main():
    BUILD.mkdir(parents=True, exist_ok=True)
    beats = json.loads((ROOT / "beats.json").read_text())

    # Prefer live UI for middle beats when available
    ui_map = {
        "02_console": ("ui_02_console.png", "Console · laptop · Ollama Qwen2.5-7B online"),
        "03_audit_gaps": ("ui_03_audit_gaps.png", "CASE-1042 audit · 60% · missing env + nvidia-smi"),
        "04_inject_investigate": ("ui_04_llm_report.png", "Live LLM report · cites CUDA OOM + train_scratch.py"),
        "05_eval": ("ui_05_eval.png", "Eval board · rule goldens 5/5 · avg 95"),
        "06_security": ("ui_06_security.png", "Security gate · shell / GPU reset denied"),
    }

    # Also keep LLM report as extra mid frame if present
    llm_shot = find_shot("ui_04_llm_report.png")

    sequence: list[tuple[Path, float, str]] = []
    for b in beats:
        wav = AUDIO / f"{b['file']}.wav"
        dur = wav_duration(wav)
        title = FRAMES / f"{b['file']}.png"
        ui_name, caption = ui_map.get(b["file"], (None, None))
        shot = find_shot(ui_name) if ui_name else None

        if shot and title.exists():
            # half title, half live UI for that beat
            d1 = max(2.5, dur * 0.38)
            d2 = max(2.5, dur - d1)
            sequence.append((title, d1, wav.name + ":title"))
            ui_frame = BUILD / f"{b['file']}_ui.png"
            fit_ui(shot, caption).save(ui_frame)
            sequence.append((ui_frame, d2, wav.name + ":ui"))
        else:
            sequence.append((title, dur, wav.name))

    # Insert LLM report briefly into beat 04 ui portion if we have it (already mapped inject)
    if llm_shot:
        # replace nothing — add a short silent? Skip; inject shot is enough.
        pass

    # Build per-beat video segments (image + matching audio), then concat
    seg_list = BUILD / "segments.txt"
    segment_paths = []
    for i, b in enumerate(beats):
        wav = AUDIO / f"{b['file']}.wav"
        dur = wav_duration(wav)
        title = FRAMES / f"{b['file']}.png"
        ui_name, caption = ui_map.get(b["file"], (None, None))
        shot = find_shot(ui_name) if ui_name else None

        # Create a still video for the beat duration using slideshow of title[+ui]
        stills = BUILD / f"stills_{b['id']}"
        if stills.exists():
            shutil.rmtree(stills)
        stills.mkdir()
        frames_meta = []
        if shot:
            d1 = dur * 0.4
            d2 = dur - d1
            frames_meta.append((title, d1))
            ui_img = fit_ui(shot, caption or "")
            ui_path = stills / "ui.png"
            ui_img.save(ui_path)
            # crossfade frames written as short sequence at end of title
            frames_meta.append((ui_path, d2))
        else:
            frames_meta.append((title, dur))

        # ffmpeg concat demuxer for images with durations
        concat_img = stills / "images.txt"
        lines = []
        for img, d in frames_meta:
            lines.append(f"file '{img.resolve()}'")
            lines.append(f"duration {d:.3f}")
        # last file repeated for concat demuxer
        lines.append(f"file '{frames_meta[-1][0].resolve()}'")
        concat_img.write_text("\n".join(lines) + "\n")

        seg = BUILD / f"seg_{b['id']}.mp4"
        cmd = [
            FFMPEG, "-y",
            "-f", "concat", "-safe", "0", "-i", str(concat_img),
            "-i", str(wav),
            "-vf", f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,fps=30,format=yuv420p",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            "-movflags", "+faststart",
            str(seg),
        ]
        print("encoding", seg.name, f"{dur:.1f}s")
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        segment_paths.append(seg)

    seg_list.write_text("".join(f"file '{p.resolve()}'\n" for p in segment_paths))
    cmd = [
        FFMPEG, "-y",
        "-f", "concat", "-safe", "0", "-i", str(seg_list),
        "-c", "copy",
        str(OUT),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # total duration
    total = sum(wav_duration(AUDIO / f"{b['file']}.wav") for b in beats)
    print("OUTPUT", OUT)
    print(f"DURATION_SEC {total:.1f}")
    print(f"SIZE_MB {OUT.stat().st_size / 1e6:.1f}")


if __name__ == "__main__":
    main()
