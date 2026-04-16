import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from ..config import settings


class SessionService:
    def __init__(self):
        # 会话存储在项目根目录的sessions目录
        self.sessions_dir = settings.project_root / "sessions"
        self.sessions_dir.mkdir(exist_ok=True)

    def _get_session_file(self, session_id: str) -> Path:
        """获取会话文件路径"""
        return self.sessions_dir / f"{session_id}.jsonl"

    def _get_session_metadata_file(self, session_id: str) -> Path:
        """获取会话元数据文件路径"""
        return self.sessions_dir / f"{session_id}_metadata.json"

    def create_session(self) -> str:
        """创建新会话，返回会话ID"""
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        # 创建空的会话文件
        self._get_session_file(session_id).touch()
        return session_id

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        options: Optional[List[Dict]] = None,
        uploaded_file: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """添加消息到会话"""
        message = {
            "timestamp": datetime.now().isoformat(),
            "role": role,
            "content": content,
            "options": options or []
        }

        # 如果有文件信息，添加到消息中
        if uploaded_file:
            message["uploaded_file"] = uploaded_file

        session_file = self._get_session_file(session_id)
        with open(session_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(message, ensure_ascii=False) + "\n")

        return message

    def get_messages(self, session_id: str) -> List[Dict[str, Any]]:
        """获取会话的所有消息"""
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

    def add_session_file(self, session_id: str, unique_filename: str, file_data: Dict[str, Any]):
        """添加文件到会话（支持多文件）"""
        metadata_file = self._get_session_metadata_file(session_id)

        # 读取现有元数据
        if metadata_file.exists():
            with open(metadata_file, "r", encoding="utf-8") as f:
                metadata = json.load(f)
        else:
            metadata = {"uploaded_files": []}

        # 从file_data中提取信息
        original_filename = file_data.get("original_filename", unique_filename)
        content = file_data.get("content", {})

        file_entry = {
            "filename": unique_filename,  # 唯一文件名（用于下载）
            "original_filename": original_filename,  # 原始文件名（用于显示）
            "content": content,
            "size": file_data.get("size", 0),
            "uploaded_at": datetime.now().isoformat()
        }

        # 添加到文件列表
        if "uploaded_files" not in metadata:
            metadata["uploaded_files"] = []
        metadata["uploaded_files"].append(file_entry)

        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

    def get_session_file(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话关联的最新文件（保持向后兼容）"""
        metadata_file = self._get_session_metadata_file(session_id)
        if not metadata_file.exists():
            return None

        with open(metadata_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)

            # 支持新的多文件格式
            if "uploaded_files" in metadata and metadata["uploaded_files"]:
                return metadata["uploaded_files"][-1]  # 返回最新的文件
            # 兼容旧的单文件格式
            return metadata.get("uploaded_file")

    def get_session_files(self, session_id: str) -> List[Dict[str, Any]]:
        """获取会话关联的所有文件"""
        metadata_file = self._get_session_metadata_file(session_id)
        if not metadata_file.exists():
            return []

        with open(metadata_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)

            # 支持新的多文件格式
            if "uploaded_files" in metadata:
                return metadata["uploaded_files"]
            # 兼容旧的单文件格式
            if "uploaded_file" in metadata:
                return [metadata["uploaded_file"]]
            return []

    def clear_session_file(self, session_id: str):
        """清除会话关联的文件"""
        metadata_file = self._get_session_metadata_file(session_id)
        if metadata_file.exists():
            metadata_file.unlink()

    def list_sessions(self) -> List[Dict[str, Any]]:
        """列出所有会话"""
        sessions = []
        for session_file in sorted(self.sessions_dir.glob("*.jsonl"), reverse=True):
            session_id = session_file.stem
            messages = self.get_messages(session_id)

            if messages:
                # 获取关联的所有文件
                uploaded_files = self.get_session_files(session_id)

                sessions.append({
                    "id": session_id,
                    "created_at": messages[0]["timestamp"],
                    "last_message": messages[-1]["content"][:50] if messages else "",
                    "message_count": len(messages),
                    "has_file": len(uploaded_files) > 0,
                    "file_count": len(uploaded_files),
                    "file_names": [f.get("original_filename") for f in uploaded_files]
                })

        return sessions

    def delete_session(self, session_id: str) -> bool:
        """删除会话"""
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
        """获取或创建会话"""
        if session_id:
            session_file = self._get_session_file(session_id)
            if session_file.exists():
                return session_id

        # 创建新会话
        return self.create_session()
