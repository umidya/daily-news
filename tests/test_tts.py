import pytest

import daily_news.tts as tts
from daily_news.tts import _chunk_script, CHUNK_CHAR_LIMIT


def test_short_script_one_chunk():
    text = "This is short."
    chunks = _chunk_script(text)
    assert chunks == [text]


def test_long_script_split_at_sentence_boundary():
    sentence = "This is a fairly substantial sentence about news. "
    text = sentence * 200
    chunks = _chunk_script(text, limit=500)
    assert len(chunks) > 1
    for c in chunks:
        assert len(c) <= 500
        # Each chunk should end with sentence-ending punctuation
        assert c.rstrip()[-1] in ".!?"


def test_default_limit_under_openai_cap():
    assert CHUNK_CHAR_LIMIT < 4096


# --- silent-segment guard (regression for 2026-06-03 silent Marketing audio) ---

class _FakeResp:
    def __init__(self, content):
        self.content = content


class _FakeSpeech:
    def create(self, **_kwargs):
        return _FakeResp(b"FAKE-MP3-BYTES")


class _FakeAudio:
    speech = _FakeSpeech()


class _FakeClient:
    def __init__(self, *_a, **_k):
        self.audio = _FakeAudio()


def _segment(text="Hello world.", role="section", topic_key="ai"):
    return {"text": text, "role": role, "topic_key": topic_key}


@pytest.fixture
def _patched(monkeypatch):
    # Never construct a real OpenAI client or measure real MP3s.
    monkeypatch.setattr(tts, "OpenAI", _FakeClient)
    monkeypatch.setattr(tts, "_measure_mp3_seconds", lambda _b: 5.0)


def test_silent_segment_retried_then_succeeds(tmp_path, monkeypatch, _patched):
    # First analysis reports silence, retry reports normal speech.
    volumes = iter([-91.0, -7.0])
    monkeypatch.setattr(tts, "_max_volume_db", lambda _b: next(volumes))
    out = tmp_path / "out.mp3"
    result = tts.synthesize_segments([_segment()], out, api_key="k")
    assert len(result) == 1
    assert result[0]["duration_seconds"] == 5.0
    assert out.exists()


def test_persistently_silent_segment_raises(tmp_path, monkeypatch, _patched):
    monkeypatch.setattr(tts, "_max_volume_db", lambda _b: -95.0)
    with pytest.raises(RuntimeError, match="silent"):
        tts.synthesize_segments([_segment()], tmp_path / "out.mp3", api_key="k")


def test_guard_skipped_when_volume_unknown(tmp_path, monkeypatch, _patched):
    # ffmpeg unavailable -> _max_volume_db returns None -> proceed, no raise.
    monkeypatch.setattr(tts, "_max_volume_db", lambda _b: None)
    result = tts.synthesize_segments([_segment()], tmp_path / "out.mp3", api_key="k")
    assert len(result) == 1


def test_max_volume_db_none_without_ffmpeg(monkeypatch):
    monkeypatch.setattr(tts.shutil, "which", lambda _name: None)
    assert tts._max_volume_db(b"anything") is None
