from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4


class HotspotHistoryStore:
    """Append-only JSONL storage for hotspot scan runs."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append_run(
        self,
        keywords: str,
        sources: List[str],
        markdown: str,
        cards_count: int,
        status: str = "completed",
    ) -> Dict[str, Any]:
        record = {
            "run_id": datetime.now().strftime("%Y%m%d_%H%M%S_") + uuid4().hex[:8],
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "keywords": keywords,
            "sources": sources,
            "cards_count": cards_count,
            "status": status,
            "markdown": markdown,
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        return record

    def list_runs(self, limit: int = 50) -> List[Dict[str, Any]]:
        if not self.path.exists():
            return []
        records = []
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                records.append(record)
        return list(reversed(records))[:limit]

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        for record in self.list_runs(limit=10000):
            if record.get("run_id") == run_id:
                return record
        return None

    def as_table(self, limit: int = 50) -> List[List[Any]]:
        return [
            [
                r.get("run_id", ""),
                r.get("created_at", ""),
                r.get("keywords", ""),
                ", ".join(r.get("sources", [])),
                r.get("cards_count", 0),
                r.get("status", ""),
            ]
            for r in self.list_runs(limit=limit)
        ]
