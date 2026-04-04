"""LLM-powered structured extraction from crawled page content."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _get_openai_client() -> Any:
    try:
        import openai
    except ImportError:
        sys.exit(
            "The 'openai' package is required for structured extraction.\n"
            "Install it with:  pip install openai"
        )
    return openai.OpenAI()


def extract_fields(
    text: str,
    fields: List[str],
    client: Any,
    model: str = "gpt-4o-mini",
    url: str = "",
) -> Dict[str, Optional[str]]:
    """Use an LLM to extract structured fields from page text.

    Parameters
    ----------
    text:
        The page content (markdown or plain text).
    fields:
        List of field names to extract (e.g. ["company_name", "pricing", "api_endpoints"]).
    client:
        An OpenAI client instance.
    model:
        The model to use for extraction.
    url:
        The source URL (included in the prompt for context).

    Returns
    -------
    Dict mapping each field name to its extracted value, or null if not found.
    """
    fields_description = "\n".join(f'- "{f}"' for f in fields)
    schema_fields = ", ".join(f'"{f}": "<extracted value or null>"' for f in fields)

    prompt = f"""Extract the following fields from the web page content below.
Return a JSON object with exactly these fields. If a field is not found in the content, set its value to null.
Do not add any fields that were not requested. Return ONLY the JSON object, no other text.

Fields to extract:
{fields_description}

Expected format:
{{{schema_fields}}}

Source URL: {url}

--- PAGE CONTENT ---
{text[:8000]}
"""

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        response_format={"type": "json_object"},
    )

    try:
        return json.loads(response.choices[0].message.content)
    except (json.JSONDecodeError, IndexError, AttributeError):
        logger.warning("Failed to parse extraction response for %s", url)
        return {f: None for f in fields}


def extract_from_jsonl(
    jsonl_path: str,
    fields: List[str],
    output_path: Optional[str] = None,
    model: str = "gpt-4o-mini",
    show_progress: bool = False,
) -> List[Dict]:
    """Run structured extraction on all pages in a crawl JSONL file.

    Parameters
    ----------
    jsonl_path:
        Path to pages.jsonl from the crawler.
    fields:
        Field names to extract from each page.
    output_path:
        Where to write the extracted JSONL. Defaults to <jsonl_dir>/extracted.jsonl.
    model:
        OpenAI model to use.
    show_progress:
        Print progress.

    Returns
    -------
    List of dicts, one per page, with url, title, and extracted fields.
    """
    client = _get_openai_client()

    pages: List[Dict] = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                pages.append(json.loads(line))

    if not pages:
        logger.warning("No pages found in %s", jsonl_path)
        return []

    if output_path is None:
        output_path = str(Path(jsonl_path).parent / "extracted.jsonl")

    results: List[Dict] = []

    with open(output_path, "w", encoding="utf-8") as out:
        for i, page in enumerate(pages):
            if show_progress:
                print(f"[extract] {i + 1}/{len(pages)} — {page.get('url', '')}")

            extracted = extract_fields(
                text=page.get("text", ""),
                fields=fields,
                client=client,
                model=model,
                url=page.get("url", ""),
            )

            row = {
                "url": page.get("url", ""),
                "title": page.get("title", ""),
                **extracted,
            }
            results.append(row)

            out.write(json.dumps(row, ensure_ascii=False) + "\n")

    if show_progress:
        print(f"[done] extracted {len(results)} page(s) -> {output_path}")

    return results
