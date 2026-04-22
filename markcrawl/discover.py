"""Seed discovery — ``markcrawl discover`` subcommand.

Emits candidate crawl URLs to stdout so they can be piped into
``markcrawl --seed-file -``.  Two modes:

* ``--pack <name>``: reads a curated seed list from ``markcrawl/seeds/``.
  Ships today.
* ``--provider <name>``: calls a search API.  Stubbed; prints a "coming soon"
  message.  The flag is kept so the shape of the CLI stays stable once a
  provider lands.
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import List, Optional

SEEDS_DIR = os.path.join(os.path.dirname(__file__), "seeds")


def list_packs() -> List[str]:
    """Return the names of available seed packs (without extensions)."""
    if not os.path.isdir(SEEDS_DIR):
        return []
    return sorted(
        os.path.splitext(f)[0]
        for f in os.listdir(SEEDS_DIR)
        if f.endswith(".txt") and not f.startswith("_")
    )


def load_seed_pack(name: str) -> List[str]:
    """Load URLs from the seed pack *name*.

    Lines starting with ``#`` and blank lines are ignored.  Raises
    :class:`FileNotFoundError` if the pack doesn't exist.
    """
    path = os.path.join(SEEDS_DIR, f"{name}.txt")
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"Seed pack {name!r} not found in {SEEDS_DIR}. "
            f"Available: {', '.join(list_packs()) or '(none)'}"
        )
    urls: List[str] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            urls.append(line)
    return urls


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="markcrawl discover",
        description=(
            "Emit candidate crawl URLs to stdout. Pipe into "
            "`markcrawl --seed-file - --out ./out` to actually crawl them."
        ),
    )
    parser.add_argument(
        "--pack",
        metavar="NAME",
        help="Load a curated seed pack (see --list-packs for names).",
    )
    parser.add_argument(
        "--list-packs",
        action="store_true",
        help="List the seed packs bundled with markcrawl and exit.",
    )
    parser.add_argument(
        "--provider",
        choices=["brave", "duckduckgo", "reddit"],
        help="Search provider (not yet implemented — reserved for future use).",
    )
    parser.add_argument(
        "query",
        nargs="?",
        help="Free-text query (used with --provider).",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.list_packs:
        packs = list_packs()
        if not packs:
            print("(no seed packs found)", file=sys.stderr)
            return 0
        for p in packs:
            print(p)
        return 0

    if args.provider:
        print(
            f"error: --provider {args.provider!r} is not yet implemented. "
            f"For now, use --pack or write your own seed file.",
            file=sys.stderr,
        )
        return 2

    if args.pack:
        try:
            urls = load_seed_pack(args.pack)
        except FileNotFoundError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        for u in urls:
            print(u)
        return 0

    print(
        "error: supply --pack NAME, --list-packs, or --provider (future). "
        "See `markcrawl discover --help`.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
