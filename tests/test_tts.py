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
