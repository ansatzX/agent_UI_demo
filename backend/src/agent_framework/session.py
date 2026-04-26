import asyncio
from datetime import datetime, timedelta
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SessionService:
    """通用会话管理（JSONL 持久化）"""

    def __init__(self, sessions_dir: Optional[Path] = None, ttl_hours: int = 24):
        self.sessions_dir = sessions_dir or Path("sessions")
        self.sessions_dir.mkdir(exist_ok=True)
        self.session_ttl = timedelta(hours=ttl_hours)
        asyncio.create_task(self._cleanup_expired_sessions())

    def _get_session_file(self, session_id: str) -> Path:
        return self.sessions_dir / f"{session_id}.jsonl"

    def _get_session_metadata_file(self, session_id: str) -> Path:
        return self.sessions_dir / f"{session_id}_metadata.json"

    def create_session(self) -> str:
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._get_session_file(session_id).touch()
        return session_id

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        options: Optional[List[Dict]] = None,
        uploaded_file: Optional[Dict[str, Any]] = None,
        form_values: Optional[Dict[str, Any]] = None,
        tool_results: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        message = {
            "timestamp": datetime.now().isoformat(),
            "role": role,
            "content": content,
            "options": options or [],
        }
        if uploaded_file:
            message["uploaded_file"] = uploaded_file
        if form_values:
            message["form_values"] = form_values
        if tool_results:
            message["tool_results"] = tool_results

        session_file = self._get_session_file(session_id)
        with open(session_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(message, ensure_ascii=False) + "\n")
        return message

    def get_messages(self, session_id: str) -> List[Dict[str, Any]]:
        session_file = self._get_session_file(session_id)
        if not session_file.exists():
            return []
        messages = []
        with open(session_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    messages.append(json.loads(line))
        return messages

    def list_sessions(self) -> List[Dict[str, Any]]:
        sessions = []
        for session_file in sorted(self.sessions_dir.glob("*.jsonl"), reverse=True):
            session_id = session_file.stem
            messages = self.get_messages(session_id)
            if messages:
                sessions.append({
                    "id": session_id,
                    "created_at": messages[0]["timestamp"],
                    "last_message": messages[-1]["content"][:50] if messages else "",
                    "message_count": len(messages),
                })
        return sessions

    def delete_session(self, session_id: str) -> bool:
        session_file = self._get_session_file(session_id)
        metadata_file = self._get_session_metadata_file(session_id)
        deleted = False
        if session_file.exists():
            session_file.unlink()
            deleted = True
        if metadata_file.exists():
            metadata_file.unlink()
        return deleted

    def get_or_create_session(self, session_id: Optional[str] = None) -> str:
        if session_id:
            session_file = self._get_session_file(session_id)
            if session_file.exists() and not self.is_session_expired(session_id):
                return session_id
        return self.create_session()

    def is_session_expired(self, session_id: str) -> bool:
        session_file = self._get_session_file(session_id)
        if not session_file.exists():
            return True
        mtime = datetime.fromtimestamp(session_file.stat().st_mtime)
        return (datetime.now() - mtime) > self.session_ttl

    async def _cleanup_expired_sessions(self):
        while True:
            try:
                await asyncio.sleep(3600)
                cutoff_time = datetime.now() - self.session_ttl
                for session_file in self.sessions_dir.glob("*.jsonl"):
                    try:
                        mtime = datetime.fromtimestamp(session_file.stat().st_mtime)
                        if mtime < cutoff_time:
                            self.delete_session(session_file.stem)
                    except Exception as e:
                        logger.error(f"清理会话失败 {session_file}: {e}")
            except Exception as e:
                logger.error(f"会话清理任务失败: {e}", exc_info=True)
