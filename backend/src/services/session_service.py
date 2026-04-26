"""会话管理服务（扩展通用框架）"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..agent_framework.session import SessionService as BaseSessionService
from ..config import settings


class SessionService(BaseSessionService):
    """扩展的会话管理（增加文件元数据管理）"""

    def __init__(self):
        sessions_dir = settings.project_root / "sessions"
        super().__init__(sessions_dir=sessions_dir, ttl_hours=24)

    def _get_session_metadata_file(self, session_id: str) -> Path:
        return self.sessions_dir / f"{session_id}_metadata.json"

    def add_session_file(
        self, session_id: str, unique_filename: str, file_data: Dict[str, Any]
    ):
        metadata_file = self._get_session_metadata_file(session_id)
        if metadata_file.exists():
            with open(metadata_file, "r", encoding="utf-8") as f:
                metadata = json.load(f)
        else:
            metadata = {"uploaded_files": []}

        original_filename = file_data.get("original_filename", unique_filename)
        content = file_data.get("content", {})

        file_entry = {
            "filename": unique_filename,
            "original_filename": original_filename,
            "content": content,
            "size": file_data.get("size", 0),
            "uploaded_at": datetime.now().isoformat(),
        }

        if "uploaded_files" not in metadata:
            metadata["uploaded_files"] = []
        metadata["uploaded_files"].append(file_entry)

        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

    def get_session_file(self, session_id: str) -> Optional[Dict[str, Any]]:
        metadata_file = self._get_session_metadata_file(session_id)
        if not metadata_file.exists():
            return None
        with open(metadata_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)
        if "uploaded_files" in metadata and metadata["uploaded_files"]:
            return metadata["uploaded_files"][-1]
        return metadata.get("uploaded_file")

    def get_session_files(self, session_id: str) -> List[Dict[str, Any]]:
        metadata_file = self._get_session_metadata_file(session_id)
        if not metadata_file.exists():
            return []
        with open(metadata_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)
        if "uploaded_files" in metadata:
            return metadata["uploaded_files"]
        if "uploaded_file" in metadata:
            return [metadata["uploaded_file"]]
        return []

    def clear_session_file(self, session_id: str):
        metadata_file = self._get_session_metadata_file(session_id)
        if metadata_file.exists():
            metadata_file.unlink()

    def list_sessions(self) -> List[Dict[str, Any]]:
        sessions = super().list_sessions()
        for s in sessions:
            uploaded_files = self.get_session_files(s["id"])
            s["has_file"] = len(uploaded_files) > 0
            s["file_count"] = len(uploaded_files)
            s["file_names"] = [f.get("original_filename") for f in uploaded_files]
            s["files"] = [
                {
                    "display_name": f.get("original_filename"),
                    "stored_filename": f.get("filename"),
                }
                for f in uploaded_files
            ]
        return sessions
