from __future__ import annotations

import io
import logging
import re
import shutil
import subprocess
from pathlib import Path
from typing import Iterable

from openai import OpenAI

log = logging.getLogger(__name__)

OPENAI_TTS_MODEL = "tts-1-hd"
OPENAI_TTS_VOICE = "onyx"
CHUNK_CHAR_LIMIT = 3500  # OpenAI cap is 4096; leave headroom


# tts-1-hd at default speed lands around 150 wpm; rough byte/sec for fallback
# duration estimates if mutagen isn't available.
_BYTES_PER_SECOND_ESTIMATE = 12000

# A TTS response whose measured peak is at/below this (dBFS) is treated as
# silent. Real onyx narration peaks around -6 to -8 dBFS; true digital silence
# is around -91 dBFS — so -60 is a safe floor that never trips on quiet speech.
# Guards against the rare case where OpenAI returns a valid-length but
# digitally-silent MP3 (observed 2026-06-03: one tts-1-hd call came back as
# 158s of -91 dB silence and shipped unnoticed — duration + byte size looked
# normal, so nothing downstream caught it).
_SILENCE_PEAK_DB = -60.0
_SILENT_SEGMENT_RETRIES = 2


def _chunk_script(text: str, limit: int = CHUNK_CHAR_LIMIT) -> list[str]:
    """Split a long script into TTS-friendly chunks at sentence boundaries."""
    text = text.strip()
    if len(text) <= limit:
        return [text]
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if not sentence:
            continue
        if len(current) + len(sentence) + 1 > limit and current:
            chunks.append(current.strip())
            current = sentence
        else:
            current = (current + " " + sentence).strip() if current else sentence
    if current:
        chunks.append(current.strip())
    return chunks


def synthesize(
    script: str,
    output_path: Path,
    api_key: str,
    voice: str = OPENAI_TTS_VOICE,
    model: str = OPENAI_TTS_MODEL,
) -> Path:
    """Generate a single MP3 from the script, chunking if needed."""
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    if not script.strip():
        raise ValueError("Empty script")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    client = OpenAI(api_key=api_key)
    chunks = _chunk_script(script)
    log.info("Synthesizing %d audio chunk(s) to %s", len(chunks), output_path)

    # MP3 frames concatenate cleanly at the byte level; this is the simplest
    # zero-dependency way to build a single playable file from multiple TTS
    # calls. Re-muxing with ffmpeg would be cleaner but adds a system dep.
    with output_path.open("wb") as f:
        for i, chunk in enumerate(chunks):
            log.info("  chunk %d/%d (%d chars)", i + 1, len(chunks), len(chunk))
            response = client.audio.speech.create(
                model=model,
                voice=voice,
                input=chunk,
                response_format="mp3",
            )
            f.write(response.content)
    return output_path


def _synthesize_chunks(
    client: OpenAI, chunks: Iterable[str], voice: str, model: str
) -> bytes:
    """Run TTS for each chunk and concatenate the MP3 bytes."""
    parts: list[bytes] = []
    for chunk in chunks:
        response = client.audio.speech.create(
            model=model,
            voice=voice,
            input=chunk,
            response_format="mp3",
        )
        parts.append(response.content)
    return b"".join(parts)


def _max_volume_db(mp3_bytes: bytes) -> float | None:
    """Peak volume of an MP3 in dBFS via ffmpeg's volumedetect, read from
    stdin. Returns None when ffmpeg is unavailable or analysis fails — the
    caller treats 'unknown' as 'not provably silent' and proceeds. ffmpeg is
    an OPPORTUNISTIC check (present on the CI runners that produce the audio),
    never a hard runtime dependency, so local runs without it still work."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return None
    try:
        proc = subprocess.run(
            [ffmpeg, "-hide_banner", "-nostats", "-i", "pipe:0",
             "-af", "volumedetect", "-f", "null", "-"],
            input=mp3_bytes,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=120,
        )
    except Exception:  # ffmpeg missing mid-run, timeout, OS error — skip check
        return None
    for line in proc.stderr.decode("utf-8", "replace").splitlines():
        if "max_volume:" in line:
            try:
                return float(line.split("max_volume:")[1].strip().split()[0])
            except (ValueError, IndexError):
                return None
    return None


def _measure_mp3_seconds(mp3_bytes: bytes) -> float:
    """Best-effort duration in seconds from raw MP3 bytes. Uses mutagen,
    falls back to byte-rate estimate if mutagen can't parse the buffer."""
    try:
        from mutagen.mp3 import MP3  # type: ignore[import-not-found]

        return float(MP3(io.BytesIO(mp3_bytes)).info.length)
    except Exception:
        return len(mp3_bytes) / _BYTES_PER_SECOND_ESTIMATE


def synthesize_segments(
    segments: list[dict],
    output_path: Path,
    api_key: str,
    voice: str = OPENAI_TTS_VOICE,
    model: str = OPENAI_TTS_MODEL,
) -> list[dict]:
    """Synthesize each segment as its own TTS call so we can measure each
    section's actual narrated duration. Concatenates all bytes into a single
    MP3 at output_path. Returns the segments enriched with measured
    `start_seconds` and `duration_seconds` fields, in input order.

    Each input segment dict must have at least a 'text' key. Empty-text
    segments are skipped.
    """
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    if not segments:
        raise ValueError("No segments to synthesize")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    client = OpenAI(api_key=api_key)

    enriched: list[dict] = []
    cumulative = 0.0

    log.info("Synthesizing %d segment(s) to %s", len(segments), output_path)
    with output_path.open("wb") as out_f:
        for i, seg in enumerate(segments):
            text = (seg.get("text") or "").strip()
            if not text:
                log.info("  segment %d/%d skipped (empty text)", i + 1, len(segments))
                continue

            chunks = _chunk_script(text)
            log.info(
                "  segment %d/%d (role=%s, %d char%s, %d chunk%s)",
                i + 1,
                len(segments),
                seg.get("role") or "?",
                len(text),
                "s" if len(text) != 1 else "",
                len(chunks),
                "s" if len(chunks) != 1 else "",
            )

            seg_bytes = _synthesize_chunks(client, chunks, voice, model)

            # Silent-segment guard. OpenAI very occasionally returns a
            # valid-length but digitally-silent MP3; without this check it
            # ships as a section with no audio (see _SILENCE_PEAK_DB note).
            # Retry the whole segment, then fail loudly rather than publish a
            # briefing with a silent section.
            peak_db = _max_volume_db(seg_bytes)
            retries = 0
            while (
                peak_db is not None
                and peak_db <= _SILENCE_PEAK_DB
                and retries < _SILENT_SEGMENT_RETRIES
            ):
                retries += 1
                log.warning(
                    "  segment %d/%d came back silent (peak %.1f dB); "
                    "retrying TTS (%d/%d)",
                    i + 1, len(segments), peak_db, retries, _SILENT_SEGMENT_RETRIES,
                )
                seg_bytes = _synthesize_chunks(client, chunks, voice, model)
                peak_db = _max_volume_db(seg_bytes)
            if peak_db is not None and peak_db <= _SILENCE_PEAK_DB:
                raise RuntimeError(
                    f"TTS returned silent audio for segment {i + 1}/{len(segments)} "
                    f"(role={seg.get('role')!r}, topic_key={seg.get('topic_key')!r}, "
                    f"peak {peak_db:.1f} dB) after {retries} retr"
                    f"{'y' if retries == 1 else 'ies'}. Aborting so a silent "
                    f"briefing is never published."
                )

            duration_seconds = _measure_mp3_seconds(seg_bytes)
            out_f.write(seg_bytes)

            enriched.append({
                **seg,
                "start_seconds": cumulative,
                "duration_seconds": duration_seconds,
            })
            cumulative += duration_seconds

    log.info("Total measured audio: %.1fs across %d segment(s)", cumulative, len(enriched))
    return enriched
