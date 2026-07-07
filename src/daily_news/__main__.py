from __future__ import annotations

import argparse
import logging
import sys

from .config import load_config
from .pipeline import run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="daily-news")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="Run the full daily pipeline")
    p_run.add_argument(
        "--mode",
        choices=["full", "dry"],
        default=None,
        help="dry = fetch + score only, no LLM or TTS calls",
    )

    sub.add_parser("config-check", help="Load config and exit (smoke test)")

    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if args.cmd == "config-check":
        cfg = load_config()
        print(f"feeds: {len(cfg.feeds)}")
        print(f"searches: {len(cfg.searches)}")
        print(f"topics: {len(cfg.topics)}")
        print(f"target_story_count: {cfg.target_story_count}")
        print(f"anthropic_api_key set: {bool(cfg.anthropic_api_key)}")
        print(f"openai_api_key set: {bool(cfg.openai_api_key)}")
        print(f"base_url: {cfg.base_url or '(unset)'}")
        return 0

    if args.cmd == "run":
        result = run(mode=args.mode)
        print(result)
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
