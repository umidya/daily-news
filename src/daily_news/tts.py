from __future__ import annotations

import logging
import re
from pathlib import Path

from openai import OpenAI

log = logging.getLogger(__name__)

OPENAI_TTS_MODEL = "tts-1-hd"
OPENAI_TTS_VOICE = "onyx"
CHUNK_CHAR_LIMIT = 3500  # OpenAI cap is 4096; leave headroom


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
