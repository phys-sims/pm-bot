# v10 Roadmap — RAG + local vector DB (Qdrant) with provenance and reproducibility

## Purpose
Enable agents to answer “what does the repo already do?” without relying on whatever the human pasted into a plan.

RAG is not about “smart chat.” For pm-bot it is about:
- retrieving *governing docs* (specs/contracts/ADRs),
- retrieving *relevant code* (APIs, patterns, tests),
- retrieving *recent repo context* (issues/PRs),
with **provenance** and **reproducibility** so humans can trust outputs.

## Mode A assumptions (local-first)
- Single operator on localhost.
- No paid cloud dependencies.
- SQLite for control-plane metadata.
- Vectors stored in a local vector DB service (Qdrant) via docker-compose.
- Repo contents available via local clones under `/data/repos`.

## Exit criteria (definition of done)
1. A local vector store runs in docker-compose (Qdrant) with persistent volume.
2. There is an ingestion pipeline that can index:
   - docs/spec, docs/contracts, docs/adr
   - repo source code (configurable allowlist/denylist)
   - optionally GitHub issues/PRs from local cache tables
3. Retrieval returns top-k chunks with full provenance:
   - repo, commit SHA, file path/URL, line ranges, chunk_id, embedding model/version
4. ContextPack builder can include retrieval results as an explicit section:
   - deterministic ordering rules
   - manifest records retrieved chunk IDs and metadata
5. At least one LangGraph graph can call a retrieval tool/node safely:
   - retrieval is bounded by budgets and capped content size
6. There is an evaluation harness:
   - a small query set with expected sources
   - regression tests that detect retrieval drift
7. UI shows index status per repo (at least: last indexed commit, chunk count, last error) and provides “reindex” action.

## Non-goals
- Multi-tenant hosted retrieval service.
- Perfect determinism of semantic search scoring (not realistic).
- Indexing the entire world; only repos in workspace.

## Default stack decision (make a call and commit to it)
### Vector DB: Qdrant (local)
Rationale:
- Built for vectors + metadata filtering.
- Runs locally in a container with persistent disk.
- Strong filters let you enforce scope (repo/path/doc_type).

### Embedding provider
Default: use the operator’s LLM provider keys (e.g., OpenAI embeddings).
But keep a config hook to swap embeddings later.

Roadmap requirement:
- Record embedding model name + version in metadata for every chunk embedding.

## Docker-compose changes (v10)
Add a `qdrant` service:
- persistent volume mounted to `/qdrant/storage`
- exposed only to local network (no public ports unless user opts in)

Add environment variables:
- `PMBOT_VECTOR_BACKEND=qdrant`
- `PMBOT_QDRANT_URL=http://qdrant:6333`
- `PMBOT_EMBEDDING_PROVIDER=openai|local`
- `PMBOT_EMBEDDING_MODEL=...`
- `PMBOT_INDEX_MAX_FILE_BYTES=...`
- `PMBOT_INDEX_INCLUDE_GLOBS=...`
- `PMBOT_INDEX_EXCLUDE_GLOBS=...`

## Data model (SQLite) — metadata only
Even though vectors live in Qdrant, keep metadata in SQLite to:
- show status in UI,
- enable reproducibility,
- manage snapshots and jobs.

### Tables/entities (recommended minimum)
1. `index_snapshots`
   - snapshot_id
   - workspace_id
   - repo_id
   - commit_sha (what was indexed)
   - created_at
   - status (created/running/completed/failed)
   - stats_json (counts, bytes, duration)
   - last_error

2. `documents`
   - document_id
   - repo_id
   - snapshot_id
   - source_type: file | issue | pr | doc_external
   - source_id: file path or URL
   - revision: commit_sha or updated_at timestamp
   - content_hash (sha256)
   - metadata_json (lang, mime, size)

3. `chunks`
   - chunk_id (stable, content-addressed)
   - document_id
   - chunk_index
   - start_offset / end_offset (byte offsets or line ranges)
   - text_hash (sha256)
   - token_count_estimate
   - metadata_json (e.g., function name, heading)

4. `embeddings`
   - embedding_id
   - chunk_id
   - vector_backend (qdrant)
   - vector_point_id (string/integer ID in qdrant)
   - embedding_provider
   - embedding_model
   - created_at

5. `index_jobs`
   - job_id
   - repo_id
   - snapshot_id
   - status
   - started_at / finished_at
   - error
   - progress_json

This schema enables:
- “what commit is indexed?”
- “what chunks exist and where did they come from?”
- “how to reproduce the exact context pack retrieval references?”

## Stable IDs (critical for reproducibility)
### Document ID
Document can be assigned by DB, but should store:
- repo_full_name
- commit_sha
- path

### Chunk ID (must be stable)
Use content-addressing:
- chunk_id = sha256(repo_full_name + commit_sha + source_path + chunk_index + text_hash)

This ensures:
- reindexing the same commit produces the same chunk IDs
- retrieval references remain stable over time

### Qdrant point ID
Use chunk_id as point ID (string) so upserts are deterministic.

## Ingestion pipeline design
### Inputs
- repo_id and repo_full_name
- commit_sha to index
- local repo checkout path (`/data/repos/<owner>/<repo>`)
- include/exclude globs
- max file size
- doc type classification rules

### Steps (v10 ingestion job)
1. **Ensure repo is available locally**
   - if missing, clone
   - if present, fetch and checkout target commit_sha
   - store local path in repo record

2. **Select files**
   - start with docs and code:
     - docs/spec/**
     - docs/contracts/**
     - docs/adr/**
     - src/** or pm_bot/** (your code roots)
   - exclude:
     - binaries, images, large json, node_modules, dist, build
   - apply `.gitignore`-style filters + pm-bot config filters

3. **Extract text**
   - for markdown: raw text
   - for code: raw text with language tag (by extension)
   - (optional later) for PDFs: skip in v10 unless absolutely needed

4. **Chunking rules (must be explicit)**
Chunking must preserve provenance.
Recommended rules:
- Markdown: chunk by headings, cap to N tokens (e.g., 400–800 tokens)
- Code: chunk by:
  - top-level definitions (functions/classes) where possible,
  - otherwise fixed-size sliding windows with overlap (e.g., 200 lines with 40 line overlap)
- Always record line ranges in chunk metadata.

5. **Persist document + chunks to SQLite**
- upsert document by (repo_id, snapshot_id, source_id)
- store content_hash; skip re-embedding unchanged docs if same hash

6. **Compute embeddings**
- batch chunks
- call embedding provider
- record provider/model/version in embeddings table

7. **Upsert vectors into Qdrant**
- collection name: `pm_bot_chunks_v1`
- point ID: chunk_id
- payload must include:
  - repo_id, repo_full_name
  - snapshot_id, commit_sha
  - source_type, source_id (path/URL)
  - start_line, end_line
  - doc_type (spec/contract/adr/code/issue/pr)
  - text_hash, token_count_estimate

8. **Finalize snapshot**
- write stats: docs indexed, chunks indexed, bytes processed
- set snapshot status completed
- update repo.last_indexed_commit_sha

### Incremental indexing (Mode A)
In local-first mode:
- On each repo sync, detect new commit on default branch.
- If commit_sha changed, schedule a new index snapshot job.
- Keep only last N snapshots by default (e.g., 3) to avoid disk bloat.
- Provide “pin snapshot” option (do not delete) for reproducibility of important runs.

## Retrieval API design (control plane)
### Endpoint semantics
`POST /api/retrieval/query`
Input:
- workspace_id
- repo scope: repo_id or list
- query_text
- filters:
  - doc_types (spec/contract/adr/code/issue/pr)
  - path_prefixes (optional)
  - snapshot_id (optional; default latest completed)
- top_k (default 8–20)
- max_total_tokens_in_results (cap, default 1500–3000 tokens)

Output:
- list of chunks:
  - chunk_id
  - snippet text
  - provenance: repo, commit_sha, path/url, line range
  - score
  - embedding metadata (model/provider)

### Safety policy filters
Provide a “safety mode” option:
- `mode=governing_docs_only` restricts doc_types to spec/contracts/adr
This is extremely useful for tasks that must follow system rules.

## ContextPack integration (critical)
### ContextPack structure change
Add a new section type: `retrieved`.
- ContextPack must include:
  - a deterministic “core” section (selected by system rules)
  - retrieved sections (from retrieval results)

### Deterministic ordering rule
Sort retrieved chunks by:
1. doc_type priority (spec > contract > adr > code > issues > prs)
2. score bucket (e.g., 0.9–1.0, 0.8–0.9, …) to reduce nondeterministic micro-ordering
3. stable tie-breaker: chunk_id

### Manifest requirements
ContextPack manifest must record:
- retrieval query string
- snapshot_id and commit_sha
- list of chunk_ids included
- embedding model/version
- timestamp

This makes “what did the agent see?” auditable.

## LangGraph integration (execution plane)
Provide a retrieval tool accessible to graphs:
- tool name: `retrieve_context`
- input: query text + filters + top_k
- output: list of chunks with provenance

Budget enforcement:
- retrieval tool must cap:
  - max chunks
  - max tokens returned
  - max time

Interrupt gating (optional but recommended):
- if retrieval would return > threshold tokens, raise interrupt to approve spending more context.

## UI requirements (v10)
Minimal but necessary:
- Repo page shows:
  - last indexed commit_sha
  - last index job status
  - chunk count
  - last error
- Buttons:
  - “Index now”
  - “Reindex from latest commit”
  - “Delete old snapshots” (dangerous; confirm)
- Retrieval debug page (optional but very helpful):
  - query box
  - shows returned chunks and provenance

## Evaluation harness (do not skip)
### Why
RAG will drift over time as:
- chunking rules change
- embeddings change
- code changes
You need a way to detect “retrieval got worse.”

### What to build
- A small YAML/JSON file committed to repo:
  - queries
  - expected sources (path prefixes) that must appear in top_k
- A test that:
  - runs retrieval for each query
  - asserts expected sources appear in results
  - stores results snapshot for diffing

### Offline mode for CI
Because embeddings cost tokens, add a CI mode:
- run retrieval tests with a small fixed local embedding model OR
- skip embedding generation and run tests only when index exists
Pragmatic approach:
- run eval harness only in “manual” CI job or local dev until stable.

## Rollout/rollback
Feature flags:
- `PMBOT_ENABLE_RAG`
- `PMBOT_VECTOR_BACKEND=qdrant|none`
- `PMBOT_ENABLE_INDEX_WORKER`

Rollback:
- disable flags; system falls back to deterministic ContextPack core only
- do not delete existing index snapshots automatically

## Common failure modes
- Indexing too much → slow and useless retrieval.
  Fix: start with docs/spec/contracts/adr and your code root only.
- No provenance → humans won’t trust outputs.
  Fix: enforce provenance fields everywhere.
- Unbounded retrieval → token blowups.
  Fix: strict caps + budgets + optional interrupts.
- SQLite bloat from storing chunk text.
  Fix: store chunk text in filesystem or keep in DB only if small; always store big blobs as files.

