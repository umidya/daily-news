from __future__ import annotations

import io
import logging
import re
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

            seg_bytes_parts: list[bytes] = []
            for chunk in chunks:
                response = client.audio.speech.create(
                    model=model,
                    voice=voice,
                    input=chunk,
                    response_format="mp3",
                )
                seg_bytes_parts.append(response.content)
            seg_bytes = b"".join(seg_bytes_parts)

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
