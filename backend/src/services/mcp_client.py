# backend/src/services/mcp_client.py
import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class MCPProcessResult:
    """MCP 处理结果"""
    output_file: Path
    intermediate_json: Path
    images: list[Path]
    success: bool = True
    error: Optional[str] = None

class MCPClient:
    """Local Read MCP 客户端"""

    def __init__(self):
        self.process: Optional[asyncio.subprocess.Process] = None
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None

    async def connect(self) -> None:
        """连接到 MCP 服务器"""
        # 启动 MCP 服务器子进程
        self.process = await asyncio.create_subprocess_exec(
            "uv",
            "--directory", "./backend/mcp/Local_Read_MCP",
            "run", "--with", "local_read_mcp",
            "python", "-m", "local_read_mcp.server",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        self.reader = self.process.stdout
        self.writer = self.process.stdin

    async def close(self) -> None:
        """关闭连接"""
        if self.process:
            self.process.terminate()
            await self.process.wait()
            self.process = None

    async def process_document(
        self,
        file_path: Path,
        output_dir: Path
    ) -> MCPProcessResult:
        """处理文档

        Args:
            file_path: 原始文件路径
            output_dir: 输出目录

        Returns:
            MCPProcessResult: 处理结果，包含输出文件路径和状态
        """
        # 验证连接状态
        if not self.writer or not self.reader:
            logger.error("MCP 客户端未连接")
            return MCPProcessResult(
                output_file=Path(),
                intermediate_json=Path(),
                images=[],
                success=False,
                error="MCP client not connected. Call connect() first."
            )
        try:
            # 1. 构建正确的 JSON-RPC 请求
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "process_binary_file",
                    "arguments": {  # 使用 arguments 而不是其他字段
                        "file_path": str(file_path.absolute()),
                        "output_dir": str(output_dir.absolute())
                    }
                }
            }

            logger.info(f"发送 MCP 请求: {json.dumps(request, ensure_ascii=False)}")

            # 2. 发送请求
            self.writer.write((json.dumps(request) + "\n").encode())
            await self.writer.drain()

            # 3. 读取响应
            response_line = await self.reader.readline()
            response = json.loads(response_line.decode())

            logger.info(f"收到 MCP 响应: {json.dumps(response, ensure_ascii=False)[:500]}")

            # 4. 错误检查
            if "error" in response:
                error_msg = response["error"].get("message", str(response["error"]))
                logger.error(f"MCP 错误: {error_msg}")
                return MCPProcessResult(
                    output_file=Path(),
                    intermediate_json=Path(),
                    images=[],
                    success=False,
                    error=error_msg
                )

            # 5. 提取结果
            result = response.get("result", {})

            if not result.get("success", False):
                error = result.get("error", "Unknown error")
                logger.error(f"MCP 处理失败: {error}")
                return MCPProcessResult(
                    output_file=Path(),
                    intermediate_json=Path(),
                    images=[],
                    success=False,
                    error=error
                )

            # 6. 从嵌套结构提取文件路径
            files = result.get("files", {})

            # Validate required files exist
            markdown_path = files.get("markdown")
            intermediate_path = files.get("intermediate_json")

            if not markdown_path or not intermediate_path:
                error = "MCP response missing required file paths"
                logger.error(f"{error}: markdown={markdown_path}, intermediate_json={intermediate_path}")
                return MCPProcessResult(
                    output_file=Path(),
                    intermediate_json=Path(),
                    images=[],
                    success=False,
                    error=error
                )

            logger.info(f"MCP 处理成功，输出文件: {markdown_path}")

            # Process images directory
            images_dir = Path(files["images"]) if files.get("images") else None
            if images_dir and images_dir.exists() and images_dir.is_dir():
                images = list(images_dir.glob("*.png")) + list(images_dir.glob("*.jpg")) + list(images_dir.glob("*.jpeg"))
                logger.info(f"找到 {len(images)} 张图片")
            else:
                if images_dir:
                    logger.warning(f"图片目录不存在或不是目录: {images_dir}")
                images = []

            return MCPProcessResult(
                output_file=Path(markdown_path),
                intermediate_json=Path(intermediate_path),
                images=images,
                success=True
            )

        except Exception as e:
            logger.error(f"MCP 处理异常: {e}", exc_info=True)
            return MCPProcessResult(
                output_file=Path(),
                intermediate_json=Path(),
                images=[],
                success=False,
                error=str(e)
            )
