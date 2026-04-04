# Privacy Policy

**MarkCrawl by iD8**
Last updated: April 4, 2026

## Overview

MarkCrawl is an open-source web crawler that runs entirely on your local machine. This privacy policy explains what data MarkCrawl accesses, processes, and stores.

## Data MarkCrawl accesses

### Websites you crawl
- MarkCrawl fetches publicly available web pages from URLs you specify.
- It respects `robots.txt` directives and does not access pages that are disallowed.
- It does not bypass authentication, CAPTCHAs, or access controls.
- Crawled content is stored locally on your machine in the output directory you specify.

### API keys (optional features only)
- If you use the LLM extraction feature, your API key is sent to the LLM provider (OpenAI, Anthropic, Google, or xAI) along with page content for processing.
- If you use the Supabase upload feature, your Supabase credentials are used to connect to your Supabase project.
- API keys are read from environment variables and are never logged, stored to disk, or transmitted to any party other than the provider you configured.

## Data MarkCrawl does NOT collect

- MarkCrawl does **not** collect any telemetry, analytics, or usage data.
- MarkCrawl does **not** phone home to any server.
- MarkCrawl does **not** send any data to iD8, AIMLPM, or any third party.
- MarkCrawl does **not** store or transmit your API keys beyond the configured provider.

## Data storage

All data is stored locally on your machine:
- Crawled pages are saved as Markdown/text files in the output directory you specify.
- The JSONL index (`pages.jsonl`) is stored in the same output directory.
- Extracted data (`extracted.jsonl`) is stored in the same output directory.
- Crawl state (`.crawl_state.json`) is stored in the output directory for resume support.
- No data is stored outside of directories you explicitly configure.

## Third-party services

MarkCrawl optionally integrates with third-party services when you explicitly configure them:

| Service | When used | What is sent |
|---|---|---|
| OpenAI API | `--provider openai` or `markcrawl-upload` | Page text content + your API key |
| Anthropic API | `--provider anthropic` | Page text content + your API key |
| Google Gemini API | `--provider gemini` | Page text content + your API key |
| xAI (Grok) API | `--provider grok` | Page text content + your API key |
| Supabase | `markcrawl-upload` | Chunked text + embeddings + your credentials |

These services are governed by their own privacy policies. MarkCrawl does not control how they process your data.

## MCP server

When running as an MCP server, MarkCrawl operates locally and communicates only with the MCP client (e.g., Claude Desktop) on your machine. No data is sent to external servers unless you use extraction or upload features that require API keys.

## Your responsibility

- You are responsible for complying with the terms of service and privacy policies of websites you crawl.
- You are responsible for how you use, store, and share the data MarkCrawl produces.
- Only crawl content you are authorized to access.

## Changes to this policy

This policy may be updated as MarkCrawl evolves. Changes will be reflected in this file with an updated date.

## Contact

For privacy-related questions, open an issue at [github.com/AIMLPM/markcrawl](https://github.com/AIMLPM/markcrawl/issues).
