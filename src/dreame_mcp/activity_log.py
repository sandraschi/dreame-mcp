from __future__ import annotations

import csv
import io
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse


class ActivityLog:
    def __init__(self, max_entries: int = 5000):
        self._entries: list[dict[str, Any]] = []
        self._max = max_entries

    def add(self, level: str, detail: str, kind: str = "", meta: dict | None = None) -> str:
        entry_id = uuid.uuid4().hex[:12]
        self._entries.append(
            {
                "id": entry_id,
                "timestamp": datetime.now(UTC).isoformat(),
                "level": level,
                "kind": kind,
                "detail": detail,
                "meta": meta or {},
            }
        )
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
        items = self._entries
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
        self._entries.clear()

    def export_csv(self, level: str = "", kind: str = "", search: str = "") -> str:
        items = self._entries
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
        import json

        items = self._entries
        if level:
            items = [e for e in items if e["level"] == level]
        if kind:
            items = [e for e in items if e["kind"] == kind]
        if search:
            q = search.lower()
            items = [e for e in items if q in e["detail"].lower()]
        return json.dumps(items, indent=2)


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

    @router.delete("/logs")
    async def clear_logs():
        log.clear()
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
