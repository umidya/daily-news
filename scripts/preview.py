"""Render a synthetic digest HTML for visual preview without hitting any API.

    python scripts/preview.py
    open public/digests/2026-04-27.html
"""
from __future__ import annotations

import shutil
from pathlib import Path

from daily_news.config import load_config
from daily_news.render import render_digest_html, render_index_html
from daily_news.summarize import Digest


def main() -> None:
    cfg = load_config()
    cfg.base_url = "https://example.github.io/daily-news"

    digest = Digest(
        why_this_matters=(
            "Today's lineup is heavy on AI policy and Canadian higher ed. "
            "The Ontario international student invitations are worth flagging "
            "for clients in post-secondary, and the Bank of Canada commentary "
            "may shape the next round of mortgage conversations. The Vancouver "
            "short-term rental update is the kind of niche signal that rarely "
            "makes the global wires but matters here."
        ),
        sections=[
            {
                "name": "International students and higher ed",
                "topic_key": "intl_students_canada",
                "stories": [
                    {
                        "headline": "Ontario invites 2,000 international students in regional draw",
                        "summary": "Ontario issued targeted invitations through its Provincial Nominee Program, focused on regional labour gaps. The move signals continued provincial appetite for international graduates despite federal caps.",
                        "source": "CIC News",
                        "url": "https://example.com/1",
                    },
                    {
                        "headline": "Universities face rollercoaster decade as AI tests their value",
                        "summary": "A new analysis argues that institutions that fail to embed AI in curriculum will see enrolment shocks within five years. The piece names early movers and laggards by region.",
                        "source": "The PIE News",
                        "url": "https://example.com/2",
                    },
                ],
            },
            {
                "name": "AI",
                "topic_key": "ai",
                "stories": [
                    {
                        "headline": "Florida AG opens probe into ChatGPT after USF case",
                        "summary": "The probe focuses on safety guardrails for minors and could set a regulatory template that other states adopt. Brand teams using LLMs in consumer-facing products should track this closely.",
                        "source": "Axios",
                        "url": "https://example.com/3",
                    },
                    {
                        "headline": "Musk and Altman head to court over OpenAI's future",
                        "summary": "Jury selection began today in the high-profile case that will test the boundaries between non-profit governance and commercial AI ambition. The outcome could reshape how AI labs structure themselves.",
                        "source": "MIT Technology Review",
                        "url": "https://example.com/3b",
                    },
                ],
            },
            {
                "name": "Marketing",
                "topic_key": "marketing",
                "stories": [
                    {
                        "headline": "Chipotle taps Fernando Machado as chief brand officer",
                        "summary": "Machado, formerly of Burger King and Activision Blizzard, brings a track record of culture-first marketing. His mandate signals Chipotle wants brand heat, not just performance.",
                        "source": "Marketing Dive",
                        "url": "https://example.com/m1",
                    },
                ],
            },
            {
                "name": "Canadian housing and rates",
                "topic_key": "canadian_real_estate",
                "stories": [
                    {
                        "headline": "Bank of Canada signals patience on rate cuts",
                        "summary": "In remarks today, the BoC governor pushed back against expectations of an imminent rate cut, citing sticky core inflation. Mortgage renewal pricing is unlikely to ease before fall.",
                        "source": "Bank of Canada",
                        "url": "https://example.com/4",
                    },
                ],
            },
            {
                "name": "AirBnb and short-term rentals",
                "topic_key": "airbnb_policy",
                "stories": [
                    {
                        "headline": "Vancouver tightens enforcement on illegal short-term rentals",
                        "summary": "City council approved new fines and a faster takedown process for non-compliant listings. Sun Peaks operators are watching closely as the regional pressure builds.",
                        "source": "Daily Hive",
                        "url": "https://example.com/a1",
                    },
                ],
            },
        ],
        audio_script="Placeholder audio script for visual preview.",
        chosen_url_hashes=[],
        raw_response="",
    )

    html = render_digest_html(digest, "2026-04-27", "/audio/2026-04-27.mp3", cfg)
    out = Path("public/digests/2026-04-27.html")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"wrote {out}")

    shutil.copy("static/style.css", "public/style.css")
    print("wrote public/style.css")

    index_html = render_index_html(
        [
            {
                "digest_date": "2026-04-27",
                "html_url": "digests/2026-04-27.html",
                "story_count": 4,
            }
        ],
        cfg,
    )
    Path("public/index.html").write_text(index_html, encoding="utf-8")
    print("wrote public/index.html")


if __name__ == "__main__":
    main()
