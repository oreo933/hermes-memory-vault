# Architecture / 架构说明

## Overview
Hermes Memory Vault is a local-first external memory layer for Hermes Agent.

### Layers
1. **Markdown notes** — raw, human-readable memory entries.
2. **SQLite + FTS5** — local full-text index and metadata store.
3. **MCP server** — exposes memory operations as tools.

## Why this design
- Lightweight for small hosts
- Easy to inspect and back up
- No need for vector DB at the first stage
- Simple to migrate to bigger hosts later

## Upgrade path
- Add embeddings and vector search
- Add automatic summarization/compaction
- Add richer taxonomy and relations
- Add web dashboard if needed
