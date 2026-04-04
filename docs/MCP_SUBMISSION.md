# MCP Official Submission Checklist

Tracking requirements for submitting MarkCrawl to the official MCP Connectors Directory.

## Requirements

### 1. Production-ready status
- [ ] Remove "Beta" status — version must be 1.0+ or explicitly declared stable
- Current: v0.1.0 (Beta)

### 2. Privacy policy
- [x] Public privacy policy link
- Location: [PRIVACY.md](../PRIVACY.md)
- URL: `https://github.com/AIMLPM/markcrawl/blob/main/PRIVACY.md`

### 3. Safety annotations on all tools
- [x] `crawl_site` — `readOnlyHint: false`, `destructiveHint: false`, `openWorldHint: true`
- [x] `search_pages` — `readOnlyHint: true`, `destructiveHint: false`, `openWorldHint: false`
- [x] `read_page` — `readOnlyHint: true`, `destructiveHint: false`, `openWorldHint: false`
- [x] `list_pages` — `readOnlyHint: true`, `destructiveHint: false`, `openWorldHint: false`
- [x] `extract_data` — `readOnlyHint: false`, `destructiveHint: false`, `openWorldHint: true`

Rationale:
- `crawl_site` writes files to disk and makes HTTP requests → not read-only, open-world
- `search_pages`, `read_page`, `list_pages` only read local files → read-only, not open-world
- `extract_data` calls an external LLM API and writes extracted.jsonl → not read-only, open-world
- None are destructive (no deleting, no modifying external state)

### 4. Three example prompts
- [x] **Example 1:** "Crawl the Stripe API docs and summarize their authentication methods."
  - Demonstrates: `crawl_site` → `search_pages` → `read_page` flow
- [x] **Example 2:** "Research competitor1.com and competitor2.com — compare their pricing and features."
  - Demonstrates: `crawl_site` (x2) → `extract_data` with auto-fields
- [x] **Example 3:** "Crawl our company wiki and find all pages mentioning the onboarding process."
  - Demonstrates: `crawl_site` → `search_pages` flow for internal documentation

## Submission form
URL: [MCP Connectors Directory Server Review Form](https://forms.gle/mcp-server-review) *(exact URL TBD — check modelcontextprotocol.io)*

## When to submit
- After MarkCrawl reaches v1.0 (stable release)
- All checklist items above must be complete
- Test the MCP server end-to-end with Claude Desktop before submitting
