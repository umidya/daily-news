"""Compare two watchlist.yaml files and describe what moved.

The monthly sync is only trustworthy if Midya can see what it did. A roster
change is a business fact — a client went past, a lead became a prospect,
someone dropped off entirely — and it should arrive as a sentence she can
read, not as a silent file rewrite.

Usage:
    python -m daily_news.watchlist_diff OLD.yaml NEW.yaml
"""
from __future__ import annotations

import sys
from pathlib import Path

from .config import Watchlist, WatchlistOrg, load_watchlist

SECTIONS = ("clients", "prospects", "peer_orgs")


def _index(orgs: list[WatchlistOrg]) -> dict[str, WatchlistOrg]:
    return {o.org.strip().lower(): o for o in orgs if o.org.strip()}


def _descriptor(org: WatchlistOrg) -> str:
    bits = [b for b in (org.posture, org.stage, org.industry) if b]
    return f" ({', '.join(bits)})" if bits else ""


def diff_watchlists(old: Watchlist | None, new: Watchlist | None) -> list[str]:
    """Return human-readable change lines. Empty list means nothing moved."""
    if new is None:
        return ["ERROR: new watchlist could not be read."]
    if old is None:
        return ["First sync — no previous watchlist to compare against."]

    lines: list[str] = []
    for section in SECTIONS:
        before = _index(getattr(old, section))
        after = _index(getattr(new, section))
        label = section.replace("_", " ")

        for key in sorted(after.keys() - before.keys()):
            lines.append(f"ADDED   {label}: {after[key].org}{_descriptor(after[key])}")
        for key in sorted(before.keys() - after.keys()):
            lines.append(f"REMOVED {label}: {before[key].org}{_descriptor(before[key])}")
        for key in sorted(before.keys() & after.keys()):
            b, a = before[key], after[key]
            if (b.posture, b.stage) != (a.posture, a.stage):
                was = b.posture or b.stage or "—"
                now = a.posture or a.stage or "—"
                lines.append(f"CHANGED {label}: {a.org}: {was} → {now}")

    old_self = old.self_entity
    new_self = new.self_entity
    if bool(old_self) != bool(new_self):
        lines.append(
            "ADDED   self block" if new_self else "REMOVED self block (self-coverage detection is OFF)"
        )

    old_themes = set(old.thought_leadership_themes)
    new_themes = set(new.thought_leadership_themes)
    for t in sorted(new_themes - old_themes):
        lines.append(f"ADDED   theme: {t}")
    for t in sorted(old_themes - new_themes):
        lines.append(f"REMOVED theme: {t}")

    return lines


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 2:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    lines = diff_watchlists(load_watchlist(Path(args[0])), load_watchlist(Path(args[1])))
    if not lines:
        print("NO CHANGES")
        return 0
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
