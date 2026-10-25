#!/usr/bin/env python3
"""Clone AgentBreaker demo voice onto SupportForge narration via Coqui XTTS v2."""
from __future__ import annotations

import os
import re
import wave
from pathlib import Path

os.environ.setdefault("COQUI_TOS_AGREED", "1")

ROOT = Path(__file__).resolve().parent
REF = ROOT / "audio" / "voice_ref.wav"
NARRATION = (ROOT / "narration.txt").read_text().strip()
OUT_WAV = ROOT / "audio" / "narration_cloned.wav"
CHUNKS_DIR = ROOT / "audio" / "clone_chunks"


def _patch_torch() -> None:
    """PyTorch 2.6+ defaults weights_only=True; XTTS checkpoints need False."""
    import torch

    _orig = torch.load

    def _load(*a, **k):
        k.setdefault("weights_only", False)
        return _orig(*a, **k)

    torch.load = _load


def _patch_torchaudio_load() -> None:
    """Newer torchaudio requires torchcodec; load WAVs via soundfile instead."""
    import soundfile as sf
    import torch
    import torchaudio

    def _load(path, *a, **k):
        data, sr = sf.read(str(path), dtype="float32", always_2d=True)
        # (frames, channels) → (channels, frames)
        tensor = torch.from_numpy(data.T.copy())
        return tensor, int(sr)

    torchaudio.load = _load


def split_text(text: str, max_chars: int = 220) -> list[str]:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    chunks, cur = [], ""
    for s in sentences:
        trial = (cur + " " + s).strip()
        if len(trial) <= max_chars:
            cur = trial
        else:
            if cur:
                chunks.append(cur)
            if len(s) <= max_chars:
                cur = s
            else:
                words = s.split()
                buf = ""
                for w in words:
                    t2 = (buf + " " + w).strip()
                    if len(t2) <= max_chars:
                        buf = t2
                    else:
                        chunks.append(buf)
                        buf = w
                cur = buf
    if cur:
        chunks.append(cur)
    return chunks


def concat_wavs(paths: list[Path], out: Path, gap_ms: int = 180):
    frames = []
    params = None
    silence = None
    for p in paths:
        with wave.open(str(p), "rb") as w:
            if params is None:
                params = w.getparams()
                silence = (
                    b"\x00\x00"
                    * int(params.framerate * gap_ms / 1000)
                    * params.nchannels
                )
            frames.append(w.readframes(w.getnframes()))
            frames.append(silence)
    assert params is not None
    with wave.open(str(out), "wb") as w:
        w.setparams(params)
        for f in frames:
            w.writeframes(f)


def main():
    if not REF.exists():
        raise SystemExit(f"missing ref {REF}")
    CHUNKS_DIR.mkdir(parents=True, exist_ok=True)

    _patch_torch()
    _patch_torchaudio_load()

    print("Loading XTTS v2…")
    from TTS.api import TTS

    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
    try:
        import torch

        if torch.backends.mps.is_available():
            tts.to("mps")
            print("device: mps")
        else:
            print("device: cpu")
    except Exception:
        print("device: default")

    chunks = split_text(NARRATION)
    print(f"chunks: {len(chunks)}")
    paths = []
    for i, text in enumerate(chunks, 1):
        out = CHUNKS_DIR / f"c{i:02d}.wav"
        print(f"[{i}/{len(chunks)}] {text[:70]}…")
        tts.tts_to_file(
            text=text,
            speaker_wav=str(REF),
            language="en",
            file_path=str(out),
        )
        paths.append(out)

    concat_wavs(paths, OUT_WAV)
    with wave.open(str(OUT_WAV)) as w:
        print(f"OUT {OUT_WAV} sec={w.getnframes() / w.getframerate():.1f}")


if __name__ == "__main__":
    main()
