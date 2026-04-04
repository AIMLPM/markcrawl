"""CLI entry point for LLM-powered structured extraction."""

from __future__ import annotations

import argparse
import logging
import os
import sys

from .extract import extract_from_jsonl


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract structured fields from crawled pages using an LLM."
    )
    parser.add_argument(
        "--jsonl",
        required=True,
        help="Path to pages.jsonl produced by the crawler",
    )
    parser.add_argument(
        "--fields",
        required=True,
        nargs="+",
        help="Field names to extract (e.g. company_name pricing api_endpoints)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output JSONL path (default: <jsonl_dir>/extracted.jsonl)",
    )
    parser.add_argument(
        "--model",
        default="gpt-4o-mini",
        help="OpenAI model for extraction (default: gpt-4o-mini)",
    )
    parser.add_argument(
        "--show-progress",
        action="store_true",
        help="Print progress during extraction",
    )
    return parser


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = build_parser().parse_args()

    if not os.environ.get("OPENAI_API_KEY"):
        sys.exit("Error: OPENAI_API_KEY environment variable is required")

    results = extract_from_jsonl(
        jsonl_path=args.jsonl,
        fields=args.fields,
        output_path=args.output,
        model=args.model,
        show_progress=args.show_progress,
    )

    print(f"Extracted {len(results)} page(s).")


if __name__ == "__main__":
    main()
