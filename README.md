# Hermes Memory Vault

[中文](#中文) | [English](#english)

---

## 中文

**Hermes Memory Vault** 是一个面向 **Hermes Agent** 的轻量级本地外置记忆方案。

它通过 **Markdown + SQLite FTS5 + MCP** 的组合，为智能体提供可持续增长、可检索、可维护的长期记忆层。

### 设计目标
- **轻量化**：单机可运行，资源占用低
- **可读性**：原始内容以 Markdown 保存，方便人工查看
- **可检索性**：SQLite FTS5 提供本地全文检索
- **可扩展性**：通过 MCP 暴露统一工具接口，便于后续接入更多能力
- **Hermes 友好**：为 Hermes Agent 量身定制，适合本地宿主机持续运行

### 主要特性
- 本地 Markdown 记忆笔记
- SQLite FTS5 全文检索
- MCP 工具接口：新增 / 查询 / 读取 / 更新 / 最近记录
- 低资源占用，适合小内存宿主机
- 可按主题分类：`personal` / `work` / `product` / `temporary`

### 目录结构
```text
memory-vault/
├─ README.md
├─ src/
│  └─ local_memory_server.py
├─ config/
│  └─ rules.yaml
├─ examples/
└─ docs/
```

### MCP 工具
- `memory_init`
- `memory_add`
- `memory_search`
- `memory_get`
- `memory_update`
- `memory_recent`

### 快速接入 Hermes
在 `~/.hermes/config.yaml` 中加入：

```yaml
mcp_servers:
  local_memory:
    command: python3
    args:
      - /root/hermes-memory-vault/src/local_memory_server.py
    timeout: 30
    connect_timeout: 20
```

### 使用场景
- 记录用户长期偏好
- 沉淀工作写作风格
- 存储产品对比结论
- 归档临时但值得保留的对话结果

### 资源占用
本项目面向轻量宿主机设计：
- 无需单独数据库服务
- 无需向量数据库
- 单个 Python 进程即可运行

### License
MIT

---

## English

**Hermes Memory Vault** is a lightweight local external memory solution built for **Hermes Agent**.

It combines **Markdown + SQLite FTS5 + MCP** to provide a persistent, searchable, and maintainable long-term memory layer for agents.

### Design Goals
- **Lightweight**: runs locally with minimal resource usage
- **Readable**: raw notes are stored as Markdown for easy inspection
- **Searchable**: SQLite FTS5 enables local full-text search
- **Extensible**: MCP exposes a unified tool interface for future integrations
- **Hermes-friendly**: tailored for Hermes Agent on a local host machine

### Key Features
- Local Markdown memory notes
- SQLite FTS5 full-text search
- MCP tools for add / search / read / update / recent notes
- Low resource footprint, suitable for small-memory hosts
- Category-based organization: `personal` / `work` / `product` / `temporary`

### Repository Layout
```text
memory-vault/
├─ README.md
├─ src/
│  └─ local_memory_server.py
├─ config/
│  └─ rules.yaml
├─ examples/
└─ docs/
```

### MCP Tools
- `memory_init`
- `memory_add`
- `memory_search`
- `memory_get`
- `memory_update`
- `memory_recent`

### Quick Hermes Integration
Add this to `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  local_memory:
    command: python3
    args:
      - /root/hermes-memory-vault/src/local_memory_server.py
    timeout: 30
    connect_timeout: 20
```

### Use Cases
- Persisting long-term user preferences
- Saving writing style and work conventions
- Storing product comparison conclusions
- Archiving temporary but valuable conversation outcomes

### Resource Usage
Designed for lightweight hosts:
- No separate database server required
- No vector database required
- Runs with a single Python process

### License
MIT


## Release
- v0.1.0: Initial public release.
