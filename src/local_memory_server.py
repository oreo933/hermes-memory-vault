#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

BASE_DIR = Path(os.path.expanduser("~/.hermes/memory-vault"))
DB_PATH = BASE_DIR / "db" / "memory.db"
NOTES_DIR = BASE_DIR / "notes"
LOG_PATH = BASE_DIR / "logs" / "ingest.log"
ALLOWED_CATEGORIES = {"personal", "work", "product", "temporary"}

mcp = FastMCP("local-memory")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_dirs() -> None:
    for path in [BASE_DIR, NOTES_DIR, DB_PATH.parent, LOG_PATH.parent]:
        path.mkdir(parents=True, exist_ok=True)
    for cat in ALLOWED_CATEGORIES:
        (NOTES_DIR / cat).mkdir(parents=True, exist_ok=True)


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn


def init_db() -> None:
    ensure_dirs()
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS notes (
                id TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT NOT NULL DEFAULT '[]',
                source TEXT NOT NULL DEFAULT 'chat',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                importance INTEGER NOT NULL DEFAULT 3,
                note_path TEXT NOT NULL
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
                id UNINDEXED,
                title,
                content,
                tags,
                tokenize = 'unicode61'
            );

            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                action TEXT NOT NULL,
                target_id TEXT NOT NULL,
                detail TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )


def normalize_category(category: Optional[str]) -> str:
    if not category:
        return "temporary"
    c = category.strip().lower()
    return c if c in ALLOWED_CATEGORIES else "temporary"


def normalize_tags(tags: Optional[list[str] | str]) -> list[str]:
    if tags is None:
        return []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    out = []
    seen = set()
    for t in tags:
        t = str(t).strip().lower()
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out


def safe_title(title: str) -> str:
    title = " ".join(title.strip().split())
    return title[:80] if title else "untitled"


def note_file_path(category: str, created_at: str, note_id: str, title: str) -> Path:
    date_prefix = created_at[:10]
    slug = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in title.lower()).strip("-")
    slug = slug[:40] or "note"
    return NOTES_DIR / category / f"{date_prefix}-{slug}-{note_id[:8]}.md"


def write_markdown(path: Path, meta: dict, content: str) -> None:
    frontmatter = "\n".join([
        "---",
        *(f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in meta.items()),
        "---",
        "",
    ])
    path.write_text(frontmatter + content.strip() + "\n", encoding="utf-8")


def log_event(action: str, target_id: str, detail: dict) -> None:
    payload = {"ts": now_iso(), "action": action, "target_id": target_id, "detail": detail}
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO events (id, action, target_id, detail, created_at) VALUES (?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), action, target_id, json.dumps(detail, ensure_ascii=False), now_iso()),
        )


@mcp.tool(description="Initialize the lightweight local memory vault database and folders.")
def memory_init() -> dict:
    init_db()
    return {
        "status": "ok",
        "db_path": str(DB_PATH),
        "notes_dir": str(NOTES_DIR),
        "categories": sorted(ALLOWED_CATEGORIES),
    }


@mcp.tool(description="Add a memory note into the local vault and index it for search.")
def memory_add(title: str, content: str, category: str = "temporary", tags: Optional[list[str]] = None, source: str = "chat", importance: int = 3) -> dict:
    init_db()
    note_id = str(uuid.uuid4())
    category = normalize_category(category)
    tags_list = normalize_tags(tags)
    created_at = now_iso()
    updated_at = created_at
    title = safe_title(title)
    importance = max(1, min(5, int(importance)))
    path = note_file_path(category, created_at, note_id, title)
    meta = {
        "id": note_id,
        "category": category,
        "tags": tags_list,
        "source": source,
        "created_at": created_at,
        "updated_at": updated_at,
        "importance": importance,
    }
    write_markdown(path, meta, content)
    tags_json = json.dumps(tags_list, ensure_ascii=False)
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO notes (id, category, title, content, tags, source, created_at, updated_at, importance, note_path) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (note_id, category, title, content, tags_json, source, created_at, updated_at, importance, str(path)),
        )
        conn.execute(
            "INSERT INTO notes_fts (id, title, content, tags) VALUES (?, ?, ?, ?)",
            (note_id, title, content, " ".join(tags_list)),
        )
    log_event("add", note_id, {"title": title, "category": category, "tags": tags_list})
    return {"status": "ok", "id": note_id, "path": str(path)}


@mcp.tool(description="Search the local memory vault by keywords, optional category, and optional tag.")
def memory_search(query: str, category: Optional[str] = None, tag: Optional[str] = None, limit: int = 5) -> dict:
    init_db()
    limit = max(1, min(20, int(limit)))
    category = normalize_category(category) if category else None
    tag = tag.strip().lower() if tag else None

    filters = []
    params = []
    if category:
        filters.append("n.category = ?")
        params.append(category)
    if tag:
        filters.append("instr(lower(n.tags), ?) > 0")
        params.append(tag)
    where_clause = (" AND " + " AND ".join(filters)) if filters else ""

    rows = []
    with get_conn() as conn:
        try:
            fts_sql = (
                "SELECT n.id, n.category, n.title, n.tags, n.updated_at, n.importance, substr(n.content, 1, 220) AS snippet "
                "FROM notes_fts f JOIN notes n ON n.id = f.id WHERE notes_fts MATCH ?"
                + where_clause +
                " ORDER BY n.importance DESC, n.updated_at DESC LIMIT ?"
            )
            fts_params = [query] + params + [limit]
            rows = [dict(r) for r in conn.execute(fts_sql, fts_params).fetchall()]
        except sqlite3.OperationalError:
            rows = []

        if not rows:
            like_sql = (
                "SELECT n.id, n.category, n.title, n.tags, n.updated_at, n.importance, substr(n.content, 1, 220) AS snippet "
                "FROM notes n WHERE (n.title LIKE ? OR n.content LIKE ? OR n.tags LIKE ?)"
                + where_clause +
                " ORDER BY n.importance DESC, n.updated_at DESC LIMIT ?"
            )
            needle = f"%{query}%"
            like_params = [needle, needle, needle] + params + [limit]
            rows = [dict(r) for r in conn.execute(like_sql, like_params).fetchall()]

    for row in rows:
        try:
            row["tags"] = json.loads(row["tags"])
        except Exception:
            pass
    return {"status": "ok", "count": len(rows), "items": rows}


@mcp.tool(description="Get one memory note by id.")
def memory_get(note_id: str) -> dict:
    init_db()
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
    if not row:
        return {"status": "not_found", "id": note_id}
    item = dict(row)
    item["tags"] = json.loads(item["tags"])
    return {"status": "ok", "item": item}


@mcp.tool(description="Update content, title, tags, category, or importance for an existing memory note.")
def memory_update(note_id: str, title: Optional[str] = None, content: Optional[str] = None, category: Optional[str] = None, tags: Optional[list[str]] = None, importance: Optional[int] = None) -> dict:
    init_db()
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
        if not row:
            return {"status": "not_found", "id": note_id}
        existing = dict(row)
        new_title = safe_title(title) if title else existing["title"]
        new_content = content if content is not None else existing["content"]
        new_category = normalize_category(category) if category else existing["category"]
        new_tags = normalize_tags(tags) if tags is not None else json.loads(existing["tags"])
        new_importance = max(1, min(5, int(importance))) if importance is not None else existing["importance"]
        updated_at = now_iso()
        path = Path(existing["note_path"])
        if new_category != existing["category"]:
            path = note_file_path(new_category, existing["created_at"], note_id, new_title)
            old_path = Path(existing["note_path"])
            if old_path.exists():
                old_path.unlink()
        meta = {
            "id": note_id,
            "category": new_category,
            "tags": new_tags,
            "source": existing["source"],
            "created_at": existing["created_at"],
            "updated_at": updated_at,
            "importance": new_importance,
        }
        write_markdown(path, meta, new_content)
        conn.execute(
            "UPDATE notes SET category=?, title=?, content=?, tags=?, updated_at=?, importance=?, note_path=? WHERE id=?",
            (new_category, new_title, new_content, json.dumps(new_tags, ensure_ascii=False), updated_at, new_importance, str(path), note_id),
        )
        conn.execute("DELETE FROM notes_fts WHERE id = ?", (note_id,))
        conn.execute(
            "INSERT INTO notes_fts (id, title, content, tags) VALUES (?, ?, ?, ?)",
            (note_id, new_title, new_content, " ".join(new_tags)),
        )
    log_event("update", note_id, {"title": new_title, "category": new_category, "tags": new_tags})
    return {"status": "ok", "id": note_id, "path": str(path)}


@mcp.tool(description="Return recent memory notes for quick inspection.")
def memory_recent(limit: int = 10) -> dict:
    init_db()
    limit = max(1, min(50, int(limit)))
    with get_conn() as conn:
        rows = [dict(r) for r in conn.execute(
            "SELECT id, category, title, tags, updated_at, importance FROM notes ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        ).fetchall()]
    for row in rows:
        row["tags"] = json.loads(row["tags"])
    return {"status": "ok", "count": len(rows), "items": rows}


if __name__ == "__main__":
    init_db()
    mcp.run(transport="stdio")
