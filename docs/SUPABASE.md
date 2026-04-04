# Uploading to Supabase for RAG

After crawling with MarkCrawl, you can chunk the output, generate embeddings, and upload directly to a Supabase table with pgvector for vector search.

## 1. Set up Supabase

In your Supabase project, go to the **SQL Editor** and run:

```sql
-- Enable the pgvector extension (one time per project)
create extension if not exists vector;

-- Create the documents table
create table documents (
  id bigserial primary key,
  url text not null,
  title text,
  chunk_text text not null,
  chunk_index integer not null,
  chunk_total integer not null,
  embedding vector(1536) not null,
  metadata jsonb default '{}'::jsonb,
  created_at timestamptz default now()
);

-- Create an index for fast similarity search
create index on documents using hnsw (embedding vector_cosine_ops);
```

> **Note on dimensions:** The default embedding model (`text-embedding-3-small`) produces 1536-dimensional vectors. If you use a different model, update `vector(1536)` to match.

## 2. Set environment variables

Create a `.env` file in the project root (it is already in `.gitignore` so it won't be committed):

```bash
# .env
SUPABASE_URL="https://your-project-id.supabase.co"
SUPABASE_KEY="your-service-role-key"

# LLM API keys — only need one for extraction, OpenAI required for upload embeddings
OPENAI_API_KEY="your-openai-api-key"
ANTHROPIC_API_KEY="your-anthropic-api-key"
GEMINI_API_KEY="your-gemini-api-key"
```

Then load it before running the upload:

```bash
source .env
```

Use your **service-role key** (not the anon key) since it bypasses Row Level Security for inserts.

> **Security note:** All credentials are read from environment variables only — they are never accepted as command-line arguments to avoid leaking secrets in shell history or process listings. Never commit your `.env` file to git.

### Credential management options

| Approach | Security | Complexity | Best for |
|---|---|---|---|
| `.env` file + `.gitignore` | Basic | Low | Local dev, personal projects |
| OS keychain (macOS Keychain, etc.) | Good | Medium | Single-user local tools |
| Secret manager (AWS SSM, GCP Secret Manager, Vault) | High | Higher | Production, teams, CI/CD |

This project uses the `.env` approach. If you deploy this as a service or share it with a team, consider upgrading to a secret manager.

## 3. Run the upload

```bash
markcrawl-upload \
  --jsonl ./output/pages.jsonl \
  --show-progress
```

### Upload CLI arguments

| Argument | Description |
|---|---|
| `--jsonl` | Path to `pages.jsonl` from the crawler |
| `--table` | Target table name (default: `documents`) |
| `--max-words` | Max words per chunk (default: `400`) |
| `--overlap-words` | Overlap words between chunks (default: `50`) |
| `--embedding-model` | OpenAI embedding model (default: `text-embedding-3-small`) |
| `--show-progress` | Print progress during upload |

| Environment variable | Description |
|---|---|
| `SUPABASE_URL` | Supabase project URL (required) |
| `SUPABASE_KEY` | Supabase service-role key (required) |
| `OPENAI_API_KEY` | OpenAI API key for embeddings (required) |

## 4. Query with vector search

Once uploaded, you can find relevant chunks using cosine similarity:

```sql
-- Replace the array with your query's embedding vector
select
  url,
  title,
  chunk_text,
  1 - (embedding <=> '[0.012, -0.003, ...]') as similarity
from documents
order by embedding <=> '[0.012, -0.003, ...]'
limit 5;
```

In practice, you would generate the query embedding in your application code:

```python
import os
import openai
from supabase import create_client

supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
client = openai.OpenAI()  # uses OPENAI_API_KEY env var

# Embed the user's question
query = "How do I set up authentication?"
response = client.embeddings.create(input=[query], model="text-embedding-3-small")
query_embedding = response.data[0].embedding

# Search for the most relevant chunks
result = supabase.rpc(
    "match_documents",
    {"query_embedding": query_embedding, "match_count": 5},
).execute()

for row in result.data:
    print(f"{row['similarity']:.3f}  {row['url']}")
    print(f"  {row['chunk_text'][:120]}...\n")
```

To use the `match_documents` RPC, create this function in Supabase:

```sql
create or replace function match_documents(
  query_embedding vector(1536),
  match_count int default 5
)
returns table (
  id bigint,
  url text,
  title text,
  chunk_text text,
  similarity float
)
language sql stable
as $$
  select
    id,
    url,
    title,
    chunk_text,
    1 - (embedding <=> query_embedding) as similarity
  from documents
  order by embedding <=> query_embedding
  limit match_count;
$$;
```

## Supabase recommendations

- **HNSW index**: The `create index ... using hnsw` statement above creates an approximate nearest-neighbor index. This is much faster than exact search for tables with more than a few thousand rows. ([Supabase HNSW docs](https://supabase.com/docs/guides/ai/vector-indexes/hnsw-indexes))
- **Service-role key**: Use the service-role key for bulk inserts. For user-facing queries, use the anon key with Row Level Security enabled.
- **Embedding model**: `text-embedding-3-small` is a good balance of cost and quality. For higher accuracy, use `text-embedding-3-large` (3072 dimensions — update the `vector()` size accordingly). ([OpenAI embeddings guide](https://platform.openai.com/docs/guides/embeddings))
- **Chunk size**: The default 400 words with 50-word overlap works well for most documentation. Decrease for short-form content, increase for long technical documents.
- **pgvector reference**: The `<=>` operator is cosine distance (lower = more similar). See the [pgvector documentation](https://github.com/pgvector/pgvector) for all available distance operators.

> These recommendations were verified against official documentation as of April 2026.
