# backend/src/utils/mcp_monitor.py
"""MCP 监控和诊断工具"""
import logging
import tempfile
import shutil
from pathlib import Path
from typing import Optional
from asyncio.subprocess import Process

logger = logging.getLogger(__name__)

class MCPMonitor:
    """监控 MCP 调用的健康状态"""

    @staticmethod
    def check_mcp_process_alive(process: Optional[Process]) -> bool:
        """检查 MCP 进程是否存活

        Args:
            process: The asyncio subprocess to check, or None

        Returns:
            True if process is running, False if None or terminated
        """
        if process is None:
            return False
        # asyncio.Process 使用 returncode 而不是 poll()
        return process.returncode is None

    @staticmethod
    async def test_mcp_connection(mcp_client) -> dict:
        """测试 MCP 连接"""
        test_dir = None
        try:
            # 创建测试文件
            test_dir = Path(tempfile.mkdtemp(prefix="mcp_test_"))
            test_file = test_dir / "test.txt"
            test_file.write_text("test content")

            result = await mcp_client.process_document(test_file, test_dir)

            return {
                "success": result.success,
                "error": result.error,
                "alive": MCPMonitor.check_mcp_process_alive(mcp_client.process)
            }
        except Exception as e:
            logger.error(f"MCP 连接测试失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "alive": False
            }
        finally:
            # 清理测试文件和目录
            if test_dir and test_dir.exists():
                shutil.rmtree(test_dir, ignore_errors=True)
