"""Utilities for loading MCP server configuration.

Supports both the legacy repository format::

    {"mcpServers": [{"name": "local", "command": "uv", "args": []}]}

and the Claude/Cursor style format::

    {"mcpServers": {"zhihu": {"command": "node", "args": []}}}
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .mcp_bridge import MCPServerConfig


def load_mcp_server_configs(path: str | Path) -> List[MCPServerConfig]:
    config_path = Path(path)
    if not config_path.exists():
        return []

    data = json.loads(config_path.read_text(encoding="utf-8"))
    servers = data.get("mcpServers", [])

    if isinstance(servers, dict):
        return [
            _config_from_mapping(name=name, raw=raw)
            for name, raw in servers.items()
        ]

    if isinstance(servers, list):
        return [
            _config_from_mapping(name=raw.get("name", ""), raw=raw)
            for raw in servers
            if isinstance(raw, dict) and raw.get("command")
        ]

    return []


def _config_from_mapping(name: str, raw: Dict[str, Any]) -> MCPServerConfig:
    return MCPServerConfig(
        name=name,
        command=raw.get("command", ""),
        args=list(raw.get("args", [])),
        env=dict(raw.get("env", {})),
        description=raw.get("description", name),
    )
