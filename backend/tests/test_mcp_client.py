# backend/tests/test_mcp_client.py
import pytest
from pathlib import Path
from backend.src.services.mcp_client import MCPClient

@pytest.mark.asyncio
async def test_mcp_client_initialization():
    """测试 MCP 客户端初始化"""
    client = MCPClient()
    assert client is not None
    assert client.process is None

@pytest.mark.asyncio
async def test_mcp_client_connect():
    """测试连接到 MCP 服务器"""
    client = MCPClient()
    await client.connect()
    assert client.process is not None
    await client.close()

@pytest.mark.asyncio
async def test_mcp_process_document(tmp_path):
    """测试文档处理"""
    client = MCPClient()
    await client.connect()

    # 创建测试文件
    test_file = tmp_path / "test.docx"
    test_file.write_bytes(b"test content")

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    result = await client.process_document(test_file, output_dir)

    assert result.success
    assert result.output_file.exists()

    await client.close()
