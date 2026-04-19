# Usage / 使用说明

## 1. Start the MCP server
The server is launched by Hermes through the `mcp_servers.local_memory` entry in `~/.hermes/config.yaml`.

## 2. Available tools
- `memory_init`
- `memory_add`
- `memory_search`
- `memory_get`
- `memory_update`
- `memory_recent`

## 3. Memory categories
- `personal`
- `work`
- `product`
- `temporary`

## 4. Recommended usage
- Store stable preferences in `personal`.
- Store work conventions and recurring notes in `work`.
- Store product-related comparisons in `product`.
- Store short-lived but useful notes in `temporary`.

## 5. Backups
Back up the following paths regularly:
- `~/.hermes/memory-vault/db/`
- `~/.hermes/memory-vault/notes/`
- `~/.hermes/memory-vault/config/`
