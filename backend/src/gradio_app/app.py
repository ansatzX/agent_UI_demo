"""Gradio 前端应用 - 通用 AI Agent 交互界面"""

import logging
import os
import sys
from collections import OrderedDict
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class GradioChatHandler:
    """Gradio 聊天处理器（异步 ReAct Agent + MCP 桥）"""

    def __init__(self):
        from ..agent_framework import ReActAgent, ToolRegistry
        from ..agent_framework.mcp_bridge import MCPBridge

        self.tools = self._register_tools()
        llm = self._create_llm()

        generic_prompt = """你是一个通用智能助手，可以使用工具帮助用户完成各种任务。

## 可用工具
{tool_descriptions}

## 核心能力
1. **网页信息获取**：用户提供 URL 时，可以调用 read_webpage 爬取内容
2. **文件读取**：用户提供文件路径时，可以读取并分析文件内容
3. **信息收集**：帮助用户整理、归纳信息

## 回复风格
- 用简洁、专业的中文回复
- 主动提供下一步建议
- 不确定时，诚实告知"""
        self.agent = ReActAgent(llm, self.tools, system_prompt=generic_prompt)
        self.mcp_bridge = MCPBridge()
        self._sessions: OrderedDict = OrderedDict()
        self._max_sessions = 100

    def _create_llm(self):
        from ..services.llm_service import LLMService
        return LLMService()

    def _register_tools(self):
        from ..agent_framework import ToolRegistry
        from ..services.tools.read_webpage import ReadWebpageTool
        from ..services.tools.read_file import ReadFileTool
        from ..services.tools.show_form import ShowFormTool

        registry = ToolRegistry()
        registry.register(ReadWebpageTool())
        registry.register(ReadFileTool())
        registry.register(ShowFormTool())
        return registry

    def _history_to_agent(self, gradio_history: List) -> List[Dict]:
        agent_history = []
        if not gradio_history:
            return agent_history
        for user_msg, assistant_msg in gradio_history:
            if user_msg:
                agent_history.append({"role": "user", "content": user_msg})
            if assistant_msg:
                agent_history.append({"role": "assistant", "content": assistant_msg})
        return agent_history

    async def respond(self, message: str, history: List) -> str:
        if not message or not message.strip():
            return ""
        try:
            agent_history = self._history_to_agent(history)
            result = await self.agent.run(
                user_message=message, context={}, history=agent_history,
            )
            return result.message
        except Exception as e:
            logger.error(f"Agent 回复失败: {e}", exc_info=True)
            return f"抱歉，处理您的请求时出错: {str(e)}"

    async def respond_with_session(self, message: str, history: List, session_id: str = "default") -> str:
        result = await self.respond(message, history)
        if result and session_id in self._sessions:
            self._sessions[session_id].extend([
                {"role": "user", "content": message},
                {"role": "assistant", "content": result},
            ])
        return result

    def _format_mcp_status(self) -> List[List[str]]:
        servers = self.mcp_bridge.list_servers()
        if not servers:
            return [["暂无注册的 MCP 服务器", "", ""]]
        return [[s["name"], s["description"], "已连接" if s["connected"] else "未连接"] for s in servers]

    def get_mcp_status(self) -> List[Dict[str, str]]:
        return self.mcp_bridge.list_servers()


def create_app():
    """创建 Gradio 应用"""
    try:
        import gradio as gr
    except ImportError:
        print("请先安装 gradio: pip install gradio")
        sys.exit(1)

    handler = GradioChatHandler()

    with gr.Blocks(
        title="AI 智能助手",
        theme=gr.themes.Soft(),
        css="footer {visibility: hidden}",
    ) as demo:

        gr.Markdown("# AI 智能助手\n基于 ReAct Agent 框架的通用智能对话系统")

        with gr.Tabs():
            with gr.Tab("对话"):
                gr.ChatInterface(
                    fn=handler.respond,
                    title="",
                    description="与 AI 助手对话，可使用网页爬取、文件读取等工具",
                    theme=gr.themes.Soft(),
                )

            with gr.Tab("信息收集"):
                gr.Markdown("## 信息收集（即将上线）\n| 平台 | 状态 | 说明 |\n|------|------|------|\n| 知乎 | 开发中 | 通过 MCP 协议接入知乎信息采集 |\n| 网页 | 已支持 | 直接在对话中使用 read_webpage 工具 |")
                mcp_status = gr.Dataframe(
                    headers=["名称", "描述", "状态"],
                    value=handler._format_mcp_status(),
                    label="MCP 连接状态",
                    interactive=False,
                )
                refresh_btn = gr.Button("刷新状态", variant="secondary", size="sm")
                refresh_btn.click(fn=handler._format_mcp_status, outputs=mcp_status)
                gr.Markdown("### 未来扩展\n后续将接入知乎 MCP 服务，支持关键词搜索、热门内容采集、信息汇总与报告生成。\n*集成方式：通过 agent_framework.mcp_bridge.MCPBridge 注册即可*")

            with gr.Tab("设置"):
                gr.Markdown("## 设置\n应用配置将在后续版本中提供可视化界面。\n\n### 基础配置\n- **LLM 模型**: 通过 config.toml 配置\n- **API 密钥**: 通过环境变量或 config.toml 配置\n- **日志级别**: 通过环境变量 LOG_LEVEL 设置")

    return demo


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    app = create_app()
    port = int(os.getenv("GRADIO_PORT", "7860"))
    print(f"\n  Gradio 应用启动于 http://localhost:{port}")
    print(f"  按 Ctrl+C 停止\n")
    app.launch(server_port=port, server_name="0.0.0.0", share=False)


if __name__ == "__main__":
    main()
