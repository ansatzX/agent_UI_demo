"""Gradio 前端应用 - 通用 AI Agent 交互界面"""

import logging
import os
import sys
from collections import OrderedDict
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

DEFAULT_HOTSPOT_SOURCES = ["知乎 MCP", "Jina DeepSearch"]


class GradioChatHandler:
    """Gradio 聊天处理器（异步 ReAct Agent + MCP 桥）"""

    def __init__(self, auto_load_mcp: bool = True):
        from ..agent_framework import ReActAgent, ToolRegistry
        from ..agent_framework.mcp_bridge import MCPBridge
        from ..agent_framework.mcp_config import load_mcp_server_configs
        from ..config import settings
        from ..hotspots.history import HotspotHistoryStore

        self.tools = self._register_tools()
        self.llm = self._create_llm()

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
        self.agent = ReActAgent(self.llm, self.tools, system_prompt=generic_prompt)
        self.mcp_bridge = MCPBridge()
        self._mcp_config_path = settings.project_root / "backend" / "mcp_config.json"
        self._load_mcp_server_configs = load_mcp_server_configs
        if auto_load_mcp:
            self.load_mcp_configs()

        self.history_store = HotspotHistoryStore(settings.project_root / "sessions" / "hotspot_runs.jsonl")
        self._settings = settings
        self._hotspot_runtime: Dict[str, Any] | None = None
        self._hotspot_workflow_cls = None
        self.hotspot_workflow = None
        self._sessions: OrderedDict = OrderedDict()
        self._max_sessions = 100

    def _get_hotspot_runtime(self) -> Dict[str, Any]:
        if self._hotspot_runtime is None:
            from ..hotspots.analyzer import LLMTopicAnalyzer
            from ..hotspots.collectors.jina_deepsearch import JinaDeepSearchCollector
            from ..hotspots.collectors.zhihu_mcp import ZhihuMCPCollector
            from ..hotspots.profile import load_creator_profile
            from ..hotspots.workflow import HotspotWorkflow, render_topic_cards_markdown

            profile_path = self._settings.project_root / "backend" / "config" / "hotspot_profile.toml"
            workflow_cls = self._hotspot_workflow_cls or HotspotWorkflow
            self._hotspot_runtime = {
                "profile": load_creator_profile(profile_path),
                "workflow_cls": workflow_cls,
                "zhihu_collector": ZhihuMCPCollector(self.mcp_bridge, server_name="zhihu"),
                "jina_collector": JinaDeepSearchCollector(
                    api_key=self._settings.get_provider_api_key("aihubmix"),
                    base_url=self._settings.get_provider_api_base("aihubmix"),
                ),
                "analyzer": LLMTopicAnalyzer(self.llm),
                "render": render_topic_cards_markdown,
            }
        elif self._hotspot_workflow_cls is not None:
            self._hotspot_runtime["workflow_cls"] = self._hotspot_workflow_cls
        return self._hotspot_runtime

    def _build_hotspot_workflow(self, collectors: List[Any]):
        if self.hotspot_workflow is not None:
            return self.hotspot_workflow
        runtime = self._get_hotspot_runtime()
        return runtime["workflow_cls"](
            profile=runtime["profile"],
            collectors=collectors,
            analyzer=runtime["analyzer"],
        )

    def _render_hotspot_cards(self, cards) -> str:
        return self._get_hotspot_runtime()["render"](cards)

    def _selected_hotspot_collectors(self, selected: set[str]) -> List[Any]:
        runtime = self._get_hotspot_runtime()
        collectors = []
        if "知乎 MCP" in selected:
            collectors.append(runtime["zhihu_collector"])
        if "Jina DeepSearch" in selected:
            collectors.append(runtime["jina_collector"])
        return collectors
    def load_mcp_configs(self) -> None:
        for config in self._load_mcp_server_configs(self._mcp_config_path):
            if config.name not in self.mcp_bridge.servers:
                self.mcp_bridge.servers[config.name] = __import__(
                    "backend.src.agent_framework.mcp_bridge",
                    fromlist=["MCPServerConnection"],
                ).MCPServerConnection(config)

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
        for item in gradio_history:
            if isinstance(item, dict):
                role = item.get("role")
                content = item.get("content")
                if role in ("user", "assistant") and content:
                    agent_history.append({"role": role, "content": content})
                continue
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                user_msg, assistant_msg = item[0], item[1]
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
        return [[s["name"], s["description"], s.get("status") or ("已连接" if s["connected"] else "已配置，未连接")] for s in servers]

    def get_mcp_status(self) -> List[Dict[str, str]]:
        return self.mcp_bridge.list_servers()

    def format_mcp_status_markdown(self) -> str:
        rows = self._format_mcp_status()
        lines = ["| 名称 | 描述 | 状态 |", "|---|---|---|"]
        for name, desc, status in rows:
            lines.append(f"| {name} | {desc} | {status} |")
        return "\n".join(lines)

    def format_hotspot_history_markdown(self) -> str:
        rows = self.history_store.as_table(limit=20)
        if not rows:
            return "暂无巡检历史。"
        lines = ["| run_id | 时间 | 关键词 | 数据源 | 选题数 | 状态 |", "|---|---|---|---|---:|---|"]
        for run_id, created_at, keywords, sources, count, status in rows:
            lines.append(f"| `{run_id}` | {created_at} | {keywords} | {sources} | {count} | {status} |")
        return "\n".join(lines)

    def load_hotspot_history_detail_by_id(self, run_id: str) -> str:
        run_id = (run_id or "").strip()
        if not run_id:
            return "请输入 run_id。"
        record = self.history_store.get_run(run_id)
        if not record:
            return f"未找到历史记录：{run_id}"
        return record.get("markdown", "")


    async def connect_mcp_servers(self) -> str:
        self.load_mcp_configs()
        # Hotspot workspace only needs Zhihu; avoid blocking on unrelated MCP servers.
        await self.mcp_bridge.connect_server("zhihu")
        return self.format_mcp_status_markdown()

    async def scan_hotspots(
        self,
        keywords: str,
        limit: int,
        days: int,
        sources: List[str] | None = None,
    ) -> str:
        keywords = (keywords or "").strip()
        if not keywords:
            keywords = "社会热点 科技产业 国际关系 财经商业 舆论争议"
        try:
            selected = set(DEFAULT_HOTSPOT_SOURCES if sources is None else sources)
            collectors = self._selected_hotspot_collectors(selected)
            workflow = self._build_hotspot_workflow(collectors)
            cards = await workflow.scan(
                keywords=keywords,
                limit=int(limit or 10),
                days=int(days or 1),
            )
            markdown = self._render_hotspot_cards(cards)
            self.history_store.append_run(
                keywords=keywords,
                sources=list(selected),
                markdown=markdown,
                cards_count=len(cards),
            )
            return markdown
        except Exception as e:
            logger.error(f"热点巡检失败: {e}", exc_info=True)
            error = f"热点巡检失败：{e}"
            self.history_store.append_run(
                keywords=keywords,
                sources=list(sources or []),
                markdown=error,
                cards_count=0,
                status="failed",
            )
            return error

    async def scan_hotspots_progress(
        self,
        keywords: str,
        limit: int,
        days: int,
        sources: List[str] | None = None,
    ):
        keywords = (keywords or "").strip() or "社会热点 科技产业 国际关系 财经商业 舆论争议"
        selected = set(DEFAULT_HOTSPOT_SOURCES if sources is None else sources)
        if "知乎 MCP" in selected:
            self.load_mcp_configs()
        yield (
            f"⏳ 开始巡检：{keywords}\n\n数据源：{', '.join(selected)}\n\n正在检查 MCP 状态...",
            self.format_hotspot_history_markdown(),
        )
        try:
            if "知乎 MCP" in selected:
                await self.mcp_bridge.ensure_connected("zhihu")
                yield (
                    f"⏳ 开始巡检：{keywords}\n\n✅ MCP 状态已检查。正在搜集知乎热榜与搜索结果...",
                    self.format_hotspot_history_markdown(),
                )
            collectors = self._selected_hotspot_collectors(selected)
            yield (
                f"⏳ 正在调用数据源并生成 LLM 选题分析...\n\n数据源：{', '.join(selected)}",
                self.format_hotspot_history_markdown(),
            )
            workflow = self._build_hotspot_workflow(collectors)
            cards = await workflow.scan(keywords=keywords, limit=int(limit or 10), days=int(days or 1))
            markdown = self._render_hotspot_cards(cards)
            final = f"✅ 巡检完成，共生成 {len(cards)} 条候选选题。\n\n---\n\n{markdown}"
            self.history_store.append_run(
                keywords=keywords,
                sources=list(selected),
                markdown=final,
                cards_count=len(cards),
            )
            yield final, self.format_hotspot_history_markdown()
        except Exception as e:
            logger.error(f"热点巡检失败: {e}", exc_info=True)
            error = f"❌ 巡检失败：{e}"
            self.history_store.append_run(
                keywords=keywords,
                sources=list(selected),
                markdown=error,
                cards_count=0,
                status="failed",
            )
            yield error, self.format_hotspot_history_markdown()

    def format_hotspot_history(self) -> List[List[Any]]:
        return self.history_store.as_table(limit=50)

    def load_hotspot_history_detail(self, evt: Any = None) -> str:
        if evt is None:
            return "请选择一条历史记录。"
        run_id = None
        if hasattr(evt, "value") and evt.value:
            value = evt.value
            if isinstance(value, list) and value:
                run_id = value[0]
            else:
                run_id = str(value)
        elif isinstance(evt, list) and evt:
            run_id = evt[0]
        if not run_id:
            return "请选择一条历史记录。"
        record = self.history_store.get_run(str(run_id))
        if not record:
            return f"未找到历史记录：{run_id}"
        return record.get("markdown", "")


def create_app():
    """创建 Gradio 应用"""
    try:
        import gradio as gr
    except ImportError:
        print("请先安装 gradio: pip install gradio")
        sys.exit(1)

    handler = GradioChatHandler(auto_load_mcp=False)

    with gr.Blocks(title="AI 智能助手") as demo:

        gr.Markdown("# AI 智能助手\n基于 ReAct Agent 框架的通用智能对话系统")

        with gr.Tabs():
            with gr.Tab("对话"):
                gr.ChatInterface(
                    fn=handler.respond,
                    title="",
                    description="与 AI 助手对话，可使用网页爬取、文件读取等工具",
                )

            with gr.Tab("热点选题巡检", render_children=True):
                gr.Markdown("""## 热点选题巡检
定制化、一站式搜集处理热点：搜集新闻 → 整合新闻 → 给出分析角度、标题建议和思维导图。

系统会展示已配置的 MCP 状态。巡检时会自动尝试连接知乎 MCP；遇到知乎人机验证时，请按弹出的浏览器完成验证，然后点击“重连 MCP”或再次巡检。""")
                with gr.Row():
                    keywords = gr.Textbox(
                        label="巡检关键词 / 领域",
                        value="社会热点 科技产业 国际关系 财经商业 舆论争议",
                        scale=4,
                    )
                    limit = gr.Slider(label="候选数量", minimum=3, maximum=30, step=1, value=10, scale=1)
                    days = gr.Slider(label="时间范围（天）", minimum=1, maximum=7, step=1, value=1, scale=1)
                sources = gr.CheckboxGroup(
                    label="数据源",
                    choices=["知乎 MCP", "Jina DeepSearch"],
                    value=DEFAULT_HOTSPOT_SOURCES,
                )
                with gr.Row():
                    scan_btn = gr.Button("开始巡检", variant="primary")
                    connect_btn = gr.Button("重连 MCP", variant="secondary", size="sm")
                output = gr.Markdown(label="巡检进度与候选选题")
                mcp_status = gr.Markdown(
                    value=handler.format_mcp_status_markdown(),
                    label="MCP 状态",
                )
                gr.Markdown("### 巡检历史")
                history_markdown = gr.Markdown(
                    value=handler.format_hotspot_history_markdown(),
                    label="最近巡检记录",
                )
                history_refresh_btn = gr.Button("刷新历史", variant="secondary", size="sm")
                with gr.Row():
                    history_run_id = gr.Textbox(label="输入 run_id 查看详情", scale=4)
                    history_load_btn = gr.Button("查看历史详情", variant="secondary", size="sm", scale=1)
                history_detail = gr.Markdown(label="历史详情")
                scan_btn.click(
                    fn=handler.scan_hotspots_progress,
                    inputs=[keywords, limit, days, sources],
                    outputs=[output, history_markdown],
                )
                connect_btn.click(fn=handler.connect_mcp_servers, outputs=mcp_status)
                refresh_btn = gr.Button("刷新 MCP 状态", variant="secondary", size="sm")
                refresh_btn.click(fn=handler.format_mcp_status_markdown, outputs=mcp_status)
                history_refresh_btn.click(fn=handler.format_hotspot_history_markdown, outputs=history_markdown)
                history_load_btn.click(fn=handler.load_hotspot_history_detail_by_id, inputs=history_run_id, outputs=history_detail)

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
    app.launch(
        server_port=port,
        server_name=os.getenv("GRADIO_SERVER_NAME", "127.0.0.1"),
        share=False,
        theme="soft",
        css="footer {visibility: hidden}",
    )


if __name__ == "__main__":
    main()
