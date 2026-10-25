#!/usr/bin/env python3
"""Generate human neural Indian-English voice + SRT, mux onto website recording."""
from __future__ import annotations

import asyncio
import re
import subprocess
from pathlib import Path

import edge_tts
import imageio_ffmpeg

ROOT = Path(__file__).resolve().parent
NARRATION = (ROOT / "narration.txt").read_text().strip()
AUDIO_MP3 = ROOT / "audio" / "narration_neural.mp3"
AUDIO_WAV = ROOT / "audio" / "narration_neural.wav"
SRT = ROOT / "audio" / "narration.srt"
VIDEO_IN = ROOT / "raw" / "website-demo.webm"
VIDEO_OUT = ROOT / "SupportForge-Website-Demo.mp4"
DESK = Path.home() / "Desktop" / "SupportForge-Website-Demo.mp4"
# Warm, friendly Indian English — neural (not macOS say)
VOICE = "en-IN-NeerjaExpressiveNeural"
RATE = "+2%"
# imageio-ffmpeg build includes libass (needed to burn subtitles)
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


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


def wrap_caption(text: str, max_chars: int = 42) -> str:
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
    # max 2 lines for readability
    if len(lines) > 2:
        mid = len(lines) // 2
        return " ".join(lines[:mid]) + "\n" + " ".join(lines[mid:])
    return "\n".join(lines)


async def synthesize() -> list[tuple[float, float, str]]:
    """Return list of (start, end, text) cue segments from sentence boundaries."""
    ROOT.joinpath("audio").mkdir(parents=True, exist_ok=True)
    communicate = edge_tts.Communicate(NARRATION, VOICE, rate=RATE)

    # Split narration into spoken sentences for cues
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", NARRATION) if s.strip()]
    # Track audio by collecting chunk timings roughly via WordBoundary if available
    boundaries: list[tuple[float, str]] = []  # offset seconds, word
    audio = bytearray()

    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio.extend(chunk["data"])
        elif chunk["type"] in ("WordBoundary", "SentenceBoundary"):
            # offset in 100-nanosecond units in some versions; edge-tts uses seconds as float in recent
            off = chunk.get("offset", 0)
            # edge-tts reports offset/duration in ticks (100ns) historically; newer may be seconds
            if isinstance(off, (int, float)) and off > 1000:
                off = off / 10_000_000  # 100ns → seconds
            text = chunk.get("text") or chunk.get("content") or ""
            if text:
                boundaries.append((float(off), text))

    AUDIO_MP3.write_bytes(audio)
    # Convert to wav for duration probe
    subprocess.run(
        [FFMPEG, "-y", "-i", str(AUDIO_MP3), "-ar", "44100", "-ac", "1", str(AUDIO_WAV)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Build SRT from sentence list timed proportionally by character weight if no boundaries
    dur = _wav_duration(AUDIO_WAV)
    cues: list[tuple[float, float, str]] = []

    if boundaries:
        # Group words into sentences by matching sentence text progressively
        words = boundaries
        # Use proportional sentence timing from total duration as fallback grouping
        total_chars = sum(len(s) for s in sentences) or 1
        t = 0.0
        for s in sentences:
            portion = len(s) / total_chars
            span = max(1.2, portion * dur)
            start, end = t, min(dur, t + span)
            cues.append((start, end, s))
            t = end
    else:
        total_chars = sum(len(s) for s in sentences) or 1
        t = 0.0
        for s in sentences:
            portion = len(s) / total_chars
            span = max(1.4, portion * dur)
            start, end = t, min(dur, t + span)
            cues.append((start, end, s))
            t = end

    # Ensure last cue ends at audio end
    if cues:
        s0, _, tx = cues[-1]
        cues[-1] = (s0, dur, tx)

    lines = []
    for i, (a, b, text) in enumerate(cues, 1):
        lines.append(str(i))
        lines.append(f"{ts(a)} --> {ts(b)}")
        lines.append(wrap_caption(text))
        lines.append("")
    SRT.write_text("\n".join(lines), encoding="utf-8")
    print(f"audio_sec={dur:.1f} cues={len(cues)} voice={VOICE}")
    return cues


def _wav_duration(path: Path) -> float:
    import wave

    with wave.open(str(path), "rb") as w:
        return w.getnframes() / float(w.getframerate())


def mux():
    if not VIDEO_IN.exists():
        raise SystemExit(f"missing video {VIDEO_IN}")
    # Burn subtitles with force_style for clean lower-third look
    # Escape path for ffmpeg subtitles filter (macOS)
    srt_esc = str(SRT).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
    style = (
        "FontName=Arial,FontSize=18,PrimaryColour=&H00FFFFFF&,OutlineColour=&H80000000&,"
        "BackColour=&H80000000&,BorderStyle=4,Outline=1,Shadow=0,MarginV=48,Bold=0"
    )
    vf = (
        f"scale=1920:1080:force_original_aspect_ratio=decrease,"
        f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30,"
        f"subtitles={srt_esc}:force_style='{style}'"
    )
    cmd = [
        FFMPEG, "-y",
        "-i", str(VIDEO_IN),
        "-i", str(AUDIO_WAV),
        "-vf", vf,
        "-map", "0:v",
        "-map", "1:a",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        "-movflags", "+faststart",
        str(VIDEO_OUT),
    ]
    print("muxing…")
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if r.returncode != 0:
        # Fallback without burn-in if libass missing: soft subs + copy note
        print(r.stderr[-1500:])
        raise SystemExit("ffmpeg mux failed")
    VIDEO_OUT.replace  # noqa: keep
    import shutil
    shutil.copy2(VIDEO_OUT, DESK)
    shutil.copy2(VIDEO_OUT, ROOT.parent / "SupportForge-Judge-Demo.mp4")
    # duration
    probe = subprocess.run([FFMPEG, "-i", str(VIDEO_OUT)], stderr=subprocess.PIPE, text=True)
    for line in probe.stderr.splitlines():
        if "Duration" in line or "Video:" in line or "Audio:" in line:
            print(line.strip())
    print("OUT", VIDEO_OUT)
    print("DESKTOP", DESK)


async def main():
    await synthesize()
    mux()


if __name__ == "__main__":
    asyncio.run(main())
