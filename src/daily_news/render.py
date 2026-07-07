from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

from feedgen.feed import FeedGenerator
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .config import Config
from .summarize import Digest


def _env(templates_dir: Path) -> Environment:
    return Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_digest_html(
    digest: Digest, date_label: str, audio_url: str, cfg: Config
) -> str:
    env = _env(cfg.templates_dir)
    template = env.get_template("digest.html")
    return template.render(
        date_label=date_label,
        audio_url=audio_url,
        why=digest.why_this_matters,
        sections=digest.sections,
        story_count=sum(len(s.get("stories", [])) for s in digest.sections),
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )


def render_index_html(
    episodes: list[dict], cfg: Config
) -> str:
    env = _env(cfg.templates_dir)
    template = env.get_template("index.html")
    return template.render(
        episodes=episodes,
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )


def write_digest_assets(
    digest: Digest,
    audio_source: Path,
    date_label: str,
    cfg: Config,
) -> tuple[Path, Path, str, str]:
    """Copy/save audio + html into public/, return (audio_path, html_path,
    public audio URL, public html URL)."""
    audio_dir = cfg.public_dir / "audio"
    digest_dir = cfg.public_dir / "digests"
    audio_dir.mkdir(parents=True, exist_ok=True)
    digest_dir.mkdir(parents=True, exist_ok=True)

    audio_dest = audio_dir / f"{date_label}.mp3"
    if audio_source.resolve() != audio_dest.resolve():
        shutil.copy2(audio_source, audio_dest)

    audio_url = f"{cfg.base_url}/audio/{date_label}.mp3" if cfg.base_url else f"/audio/{date_label}.mp3"
    html_dest = digest_dir / f"{date_label}.html"
    html_url = (
        f"{cfg.base_url}/digests/{date_label}.html"
        if cfg.base_url
        else f"/digests/{date_label}.html"
    )
    html_dest.write_text(
        render_digest_html(digest, date_label, audio_url, cfg), encoding="utf-8"
    )

    # Copy the stylesheet next to the HTML so the page works at any URL.
    css_src = cfg.static_dir / "style.css"
    if css_src.exists():
        shutil.copy2(css_src, cfg.public_dir / "style.css")

    return audio_dest, html_dest, audio_url, html_url


def write_index(episodes: list[dict], cfg: Config) -> Path:
    index_dest = cfg.public_dir / "index.html"
    index_dest.write_text(render_index_html(episodes, cfg), encoding="utf-8")
    return index_dest


def write_podcast_feed(episodes: list[dict], cfg: Config) -> Path:
    """Generate a valid podcast RSS feed for Apple Podcasts / Overcast / etc.
    `episodes` is a list of dicts with keys: digest_date, audio_url, html_url,
    audio_path (Path), title, description, story_count."""
    fg = FeedGenerator()
    fg.load_extension("podcast")
    fg.title("Daily News (Personal Briefing)")
    fg.author({"name": "Daily News", "email": "noreply@daily-news.local"})
    fg.link(href=cfg.base_url or "https://example.com", rel="alternate")
    fg.language("en-CA")
    fg.description("A personal morning news briefing covering AI, marketing, higher education, Canadian policy, BC local news, and global business.")
    fg.podcast.itunes_category("News", "Daily News")
    fg.podcast.itunes_explicit("no")
    fg.podcast.itunes_author("Daily News")
    fg.image(f"{cfg.base_url}/cover.png" if cfg.base_url else "")

    for ep in episodes:
        fe = fg.add_entry()
        fe.id(ep["audio_url"])
        fe.title(ep["title"])
        fe.description(ep["description"])
        fe.link(href=ep["html_url"])
        fe.published(ep["published"])
        try:
            length = ep["audio_path"].stat().st_size if ep["audio_path"].exists() else 0
        except Exception:
            length = 0
        fe.enclosure(ep["audio_url"], str(length), "audio/mpeg")

    feed_path = cfg.public_dir / "feed.xml"
    fg.rss_file(str(feed_path), pretty=True)
    return feed_path
