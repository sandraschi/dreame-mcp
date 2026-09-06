from __future__ import annotations

import csv
import io
import json
import logging
import threading
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse


class ActivityLog:
    def __init__(self, max_entries: int = 5000):
        self._entries: list[dict[str, Any]] = []
        self._max = max_entries
        self._lock = threading.Lock()

    def add(self, level: str, detail: str, kind: str = "", meta: dict | None = None) -> str:
        entry_id = uuid.uuid4().hex[:12]
        entry = {
            "id": entry_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "level": level.upper() if level else "INFO",
            "kind": kind,
            "detail": detail,
            "meta": meta or {},
        }
        with self._lock:
            self._entries.append(entry)
            if len(self._entries) > self._max:
                self._entries.pop(0)
        return entry_id

    def query(
        self,
        limit: int = 50,
        offset: int = 0,
        level: str = "",
        kind: str = "",
        search: str = "",
        sort: str = "desc",
        after_id: str = "",
    ) -> dict[str, Any]:
        with self._lock:
            items = list(self._entries)
        if level:
            items = [e for e in items if e["level"] == level]
        if kind:
            items = [e for e in items if e["kind"] == kind]
        if search:
            q = search.lower()
            items = [e for e in items if q in e["detail"].lower()]
        if after_id:
            try:
                idx = next(i for i, e in enumerate(items) if e["id"] == after_id)
                items = items[idx + 1 :]
            except StopIteration:
                pass
        if sort == "desc":
            items = list(reversed(items))
        total = len(items)
        return {"entries": items[offset : offset + limit], "total": total}

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def stats(self) -> dict[str, Any]:
        with self._lock:
            rows = list(self._entries)
        by_level: dict[str, int] = {}
        by_kind: dict[str, int] = {}
        for r in rows:
            by_level[str(r.get("level", "INFO"))] = by_level.get(str(r.get("level", "INFO")), 0) + 1
            by_kind[str(r.get("kind", "unknown"))] = by_kind.get(str(r.get("kind", "unknown")), 0) + 1
        return {
            "total": len(rows),
            "max_entries": self._max,
            "by_level": by_level,
            "by_kind": by_kind,
            "oldest": rows[0]["timestamp"] if rows else None,
            "newest": rows[-1]["timestamp"] if rows else None,
        }

    def export_csv(self, level: str = "", kind: str = "", search: str = "") -> str:
        with self._lock:
            items = list(self._entries)
        if level:
            items = [e for e in items if e["level"] == level]
        if kind:
            items = [e for e in items if e["kind"] == kind]
        if search:
            q = search.lower()
            items = [e for e in items if q in e["detail"].lower()]
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow(["id", "timestamp", "level", "kind", "detail"])
        for e in items:
            w.writerow([e["id"], e["timestamp"], e["level"], e["kind"], e["detail"]])
        return out.getvalue()

    def export_json(self, level: str = "", kind: str = "", search: str = "") -> str:
        with self._lock:
            items = list(self._entries)
        if level:
            items = [e for e in items if e["level"] == level]
        if kind:
            items = [e for e in items if e["kind"] == kind]
        if search:
            q = search.lower()
            items = [e for e in items if q in e["detail"].lower()]
        return json.dumps(items, indent=2)


class ActivityLogHandler(logging.Handler):
    """Bridge Python logging -> ActivityLog so /api/logs actually has data."""

    def __init__(self, log: ActivityLog, level: int = logging.NOTSET) -> None:
        super().__init__(level)
        self._log = log

    def emit(self, record: logging.LogRecord) -> None:
        try:
            lvl = record.levelname
            if lvl == "WARN":
                lvl = "WARNING"
            msg = record.getMessage()
            if record.name == "uvicorn.access" and record.levelno < logging.WARNING:
                return
            self._log.add(lvl, msg, kind="server", meta={"logger": record.name, "module": record.module})
        except Exception:
            self.handleError(record)


def install_log_handler(log: ActivityLog, level: int = logging.INFO) -> ActivityLogHandler:
    """Attach ActivityLogHandler to root logger. Idempotent."""
    for h in logging.getLogger().handlers:
        if isinstance(h, ActivityLogHandler) and getattr(h, "_log", None) is log:
            return h
    for h in logging.getLogger("dreame-mcp").handlers:
        if isinstance(h, ActivityLogHandler) and getattr(h, "_log", None) is log:
            return h
    handler = ActivityLogHandler(log, level=level)
    handler.setLevel(level)
    logging.getLogger().addHandler(handler)
    # Don't also attach to dreame-mcp: it propagates to root, would duplicate entries.
    return handler


def create_log_router(log: ActivityLog) -> APIRouter:
    router = APIRouter()

    @router.get("/logs")
    async def get_logs(
        limit: int = Query(50, ge=1, le=500),
        offset: int = Query(0, ge=0),
        level: str = Query(""),
        kind: str = Query(""),
        search: str = Query(""),
        sort: str = Query("desc"),
        after_id: str = Query(""),
    ):
        return log.query(
            limit=limit, offset=offset, level=level, kind=kind, search=search, sort=sort, after_id=after_id
        )

    @router.get("/logs/stats")
    async def get_logs_stats():
        return log.stats()

    @router.delete("/logs")
    async def clear_logs():
        log.clear()
        log.add("WARNING", "Log buffer cleared", kind="system")
        return {"success": True}

    @router.get("/logs/export")
    async def export_logs(
        format: str = Query("json"), level: str = Query(""), kind: str = Query(""), search: str = Query("")
    ):
        if format == "csv":
            return StreamingResponse(
                io.StringIO(log.export_csv(level=level, kind=kind, search=search)),
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=logs.csv"},
            )
        return StreamingResponse(
            io.StringIO(log.export_json(level=level, kind=kind, search=search)),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=logs.json"},
        )

    return router
