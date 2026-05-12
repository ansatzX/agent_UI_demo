"""Gradio chat handler — uses shared runtime from app.state."""

from __future__ import annotations

import logging
from collections import OrderedDict
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_HOTSPOT_SOURCES = ["Web Search"]

SYSTEM_PROMPT = """你是一个通用智能助手，可以使用工具帮助用户完成各种任务。

## 可用工具
{tool_descriptions}

## 研究方法论

遇到需要查证、多源验证或深度分析的问题时，按以下框架思考：

### 约束分解
复杂问题先拆解为可独立验证的子约束。标注每个约束的类型（property/statistic/temporal/comparison 等），然后逐一查证。

### 多源交叉验证
不信任单一来源。关键事实至少找 2-3 个独立来源交叉比对。标记信息矛盾之处。

### 证据分级（三维评估）
对每个事实性陈述，用三维视角评估，不只二分"可靠/不可靠"：
- **正面证据**：有多少独立来源支持这个说法？
- **反面证据**：有没有来源提出相反说法或质疑？
- **不确定性**：多少信息缺口仍然存在？

标注最终证据等级：
- `direct_statement`(95%): 官方文件直接陈述
- `official_record`(90%): 政府/机构正式记录
- `research_finding`(85%): 同行评审研究
- `statistical_data`(85%): 可追溯统计数据
- `news_report`(75%): 正规媒体报道
- `inference`(50%): 基于证据的合理推论
- `correlation`(30%): 相关性观察
- `speculation`(10%): 猜测/未证实

**拒绝阈值**：反面证据 >25% 或正面证据 <40% 时，不应采信该声明。

### 知识缺口驱动
每轮搜索后识别仍不清晰的问题，针对性补充搜索。信息不足时标注不确定性，不强给确定结论。

## 工具分工
- **check_state**: 查看/更新研究进度，找下一个待验证的约束。每次 web_search 后调用。
- **web_search**：通用网页搜索，一次搜索多个数据源。返回摘要带源分类和证据等级。始终优先用此工具搜索，而非猜测URL。
- **read_webpage**：深度阅读单个URL。先用 web_search 找到链接，再用此工具精读。
- **deep_research**：将复杂问题分解为可验证的子约束。在开始大型研究前调用一次。

## 研究循环（必须严格遵守）

每个研究任务遵循此循环：
```
deep_research("问题") → 初始化约束清单
  │
  └─ 循环:
       ├→ check_state()                  → 查当前状态，找下一个目标约束
       ├→ web_search("目标约束搜索词")     → 多源搜索
       ├→ read_webpage(高价值URL)         → 深度阅读
       ├→ 交叉比对，评估正面/反面/不确定性 →
       ├→ check_state(N, "verified", evidence="...", positive=0.8, negative=0.1)  → 更新约束状态
       │
       └→ check_state() 返回 "sufficient: true" → 综合输出

**示例**：
用户问："量子计算在药物发现中有什么最新应用？"
1. deep_research → 5 constraints
2. check_state → 下一步: 约束#1
3. web_search("quantum computing drug discovery 2025")
4. check_state(1, "verified", "发现3篇Nature/Science论文涉及量子分子模拟")
5. check_state → 下一步: 约束#2
... 重复直到 check_state → sufficient: true
6. 综合输出，附证据等级和源URL

## 工作流程
1. 若问题复杂需查证 → 先调用 deep_research 分解约束
2. 对每个约束 → 调用 web_search 多源搜索
3. 筛选高价值链接 → 调用 read_webpage 深度阅读
4. 多源交叉比对 → 评估证据等级 → 识别知识缺口
5. 补充搜索 → 综合所有发现，附证据等级和来源

## 回复风格
- 用简洁、专业的中文回复
- 事实性陈述标注证据等级
- 不确定时诚实告知，不编造"""


class GradioChatHandler:
    """Gradio 聊天处理器 — 所有服务从 app.state 获取。"""

    def __init__(self, state: Any):
        self._state = state
        self._agent = None
        self._active_research = None
        self._sessions: OrderedDict = OrderedDict()
        self._max_sessions = 100

    @property
    def _active_research(self):
        if hasattr(self._state, 'research_holder'):
            return self._state.research_holder._active_research
        return None

    @_active_research.setter
    def _active_research(self, value):
        if hasattr(self._state, 'research_holder'):
            self._state.research_holder._active_research = value

    @property
    def _llm(self):
        return self._state.llm_service

    @property
    def _tools(self):
        return self._state.tool_registry

    @property
    def _mcp(self):
        return self._state.mcp_bridge

    @property
    def _rt(self):
        return self._state.hotspot_runtime

    # ── Agent ──────────────────────────────────────────────────────────

    def _get_agent(self):
        if self._agent is None:
            from ..agent_framework import ReActAgent
            self._agent = ReActAgent(self._llm, self._tools, system_prompt=SYSTEM_PROMPT)
        return self._agent

    async def chat(self, message: str, history: list, uploaded_file=None) -> tuple:
        agent = self._get_agent()

        context: dict = {}
        if uploaded_file:
            context["uploaded_file"] = uploaded_file

        history_for_agent = []
        if history:
            for h in history[-20:]:
                if isinstance(h, dict):
                    role = h.get("role", "")
                    content = h.get("content", "")
                    if role in ("user", "assistant") and content:
                        history_for_agent.append({"role": role, "content": content})
                elif isinstance(h, (list, tuple)) and len(h) >= 2:
                    history_for_agent.append({"role": "user", "content": str(h[0])})
                    if h[1]:
                        history_for_agent.append({"role": "assistant", "content": str(h[1])})

        result = await agent.run(message, context, history=history_for_agent)

        conversation = list(history or [])
        conversation.append({"role": "user", "content": message})
        conversation.append({"role": "assistant", "content": result.message})
        return conversation, ""

    # ── Contract ──────────────────────────────────────────────────────

    async def handle_contract(self, contract_file) -> str:
        """Analyze uploaded contract template, return form/analysis."""
        if contract_file is None:
            return "请上传一个 .docx 合同模板。"
        agent = self._get_agent()
        context = {"uploaded_file": contract_file}
        result = await agent.run(
            "请分析上传的合同模板，识别所有 {{占位符}} 并生成填写表单。",
            context, history=[],
        )
        return result.message

    # ── Hotspot scanning ───────────────────────────────────────────────

    async def scan_hotspots(self, keywords: str, limit: int, days: int) -> tuple:
        from ..hotspots.workflow import render_topic_cards_markdown

        web = self._rt.get("web_collector")
        collectors = [web] if web else []

        if not collectors:
            return "请至少选择一个数据源。", self._history_markdown()

        workflow = self._rt["workflow"]
        workflow.collectors = collectors

        try:
            cards = await workflow.scan(keywords=keywords, limit=limit, days=days)
        except Exception as exc:
            logger.exception("Hotspot scan failed")
            return f"巡检失败: {exc}", self._history_markdown()

        if not cards:
            return (
                f"未找到相关选题（关键词: {keywords}，数据源: {', '.join(sources or [])}）。"
                f"\n\n建议：调整关键词、扩大时间范围、或检查数据源连接状态。",
                self._history_markdown(),
            )

        markdown = render_topic_cards_markdown(cards)

        self._rt["history_store"].append_run(
            keywords=keywords,
            sources=list(sources or []),
            markdown=markdown,
            cards_count=len(cards),
        )
        return markdown, self._history_markdown()

    # ── MCP ────────────────────────────────────────────────────────────

    async def connect_mcp(self):
        await self._mcp.connect_all()
        return self._mcp_status()

    def _mcp_status(self) -> str:
        st = self._mcp.get_all_status()
        if not st:
            return "暂无 MCP 服务器。"
        lines = ["## MCP 状态"]
        for name, info in sorted(st.items()):
            icon = "✅" if info.get("connected") else "❌"
            tools = info.get("tools", [])
            tnames = ", ".join(t.get("name", "") for t in tools[:5]) if tools else "无"
            lines.append(f"- {icon} **{name}**: {'已连接' if info.get('connected') else '未连接'} (工具: {tnames})")
        return "\n".join(lines)

    # ── History ────────────────────────────────────────────────────────

    def _history_markdown(self) -> str:
        runs = self._rt["history_store"].list_runs(limit=10)
        if not runs:
            return "暂无巡检历史。"
        lines = ["## 最近巡检记录"]
        for r in runs:
            rid = r.get("run_id", "")
            ts = r.get("created_at", "")
            kw = r.get("keywords", "")
            src = ", ".join(r.get("sources", []))
            cnt = r.get("cards_count", 0)
            lines.append(f"- `{rid[:16]}` {ts}: {kw} ({src}) — {cnt} 选题")
        return "\n".join(lines)

    def history_detail(self, run_id: str) -> str:
        run = self._rt["history_store"].get_run(run_id)
        if not run:
            return "未找到该巡检记录。"
        return run.get("markdown", "该记录无内容。")
