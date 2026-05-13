import json

from src.agent_framework.mcp_config import load_mcp_server_configs


def test_loads_claude_style_mcp_servers(tmp_path):
    path = tmp_path / "mcp_config.json"
    path.write_text(json.dumps({
        "mcpServers": {
            "zhihu": {
                "command": "node",
                "args": ["/path/to/index.js"],
                "env": {"A": "B"},
                "description": "知乎"
            }
        }
    }), encoding="utf-8")

    configs = load_mcp_server_configs(path)

    assert len(configs) == 1
    assert configs[0].name == "zhihu"
    assert configs[0].command == "node"
    assert configs[0].args == ["/path/to/index.js"]
    assert configs[0].env == {"A": "B"}
    assert configs[0].description == "知乎"


def test_loads_legacy_list_mcp_servers(tmp_path):
    path = tmp_path / "mcp_config.json"
    path.write_text(json.dumps({
        "mcpServers": [
            {"name": "local", "command": "uv", "args": ["run"], "env": {}}
        ]
    }), encoding="utf-8")

    configs = load_mcp_server_configs(path)

    assert len(configs) == 1
    assert configs[0].name == "local"
    assert configs[0].command == "uv"
    assert configs[0].args == ["run"]
