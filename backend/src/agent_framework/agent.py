"""通用 ReAct Agent（支持可配置提示词）"""

import asyncio
from dataclasses import dataclass, field
import json
import logging
from typing import Any, Dict, List, Optional

from .llm import LLMService
from .tool_registry import ToolRegistry

logger = logging.getLogger(__name__)


@dataclass
class AgentResult:
    message: str
    options: List[Dict] = field(default_factory=list)
    tool_calls: List[Dict] = field(default_factory=list)
    tool_results: List[Dict] = field(default_factory=list)


DEFAULT_SYSTEM_PROMPT = """你是一个通用智能助手，可以调用工具来帮助用户完成各种任务。

## 可用工具
{tool_descriptions}

## 核心规则
1. 根据用户需求选择合适的工具
2. 工具执行后，根据结果继续推理或直接回复用户
3. 用简洁、专业的中文回复
"""


class ReActAgent:
    """通用 ReAct Agent（可自定义 system prompt）"""

    def __init__(
        self,
        llm_service: LLMService,
        tool_registry: ToolRegistry,
        system_prompt: Optional[str] = None,
        max_iterations: int = 10,
        timeout: int = 300,
    ):
        self.llm = llm_service
        self.tools = tool_registry
        self.system_prompt = system_prompt
        self.max_iterations = max_iterations
        self.timeout = timeout

    def set_system_prompt(self, prompt: str):
        self.system_prompt = prompt

    async def run(
        self, user_message: str, context: Dict, history: List[Dict] = None
    ) -> AgentResult:
        try:
            return await asyncio.wait_for(
                self._run_impl(user_message, context, history),
                timeout=self.timeout,
            )
        except asyncio.TimeoutError:
            logger.error(f"ReAct Agent 超时 ({self.timeout}秒)")
            return AgentResult(
                message="抱歉，处理您的请求时间过长，请简化需求或稍后重试。",
                options=[],
                tool_results=[],
            )

    async def _run_impl(
        self, user_message: str, context: Dict, history: List[Dict]
    ) -> AgentResult:
        iteration = 0
        conversation = self._build_conversation(user_message, history or [], context)
        accumulated_tool_results: List[Dict] = []
        system_prompt = self._build_system_prompt()

        while iteration < self.max_iterations:
            response = await self.llm.generate_react_response(
                system_prompt=system_prompt,
                conversation=conversation,
                tools=self.tools.get_tool_definitions(),
            )

            content = response.get("content", "")
            tool_calls = response.get("tool_calls", [])

            logger.info(
                f"ReAct Agent 第 {iteration + 1} 轮: tool_calls={len(tool_calls)}"
            )

            if not tool_calls:
                return AgentResult(
                    message=content,
                    options=[],
                    tool_results=accumulated_tool_results,
                )

            tool_results = []
            requires_user_input = False

            for tc in tool_calls:
                tool_name = tc["name"]
                tool_args = tc["arguments"]
                tool_call_id = tc["id"]

                logger.info(f"调用工具: {tool_name}({tool_args})")

                try:
                    result = await self.tools.execute(tool_name, **tool_args)
                    tool_results.append({
                        "tool_call_id": tool_call_id,
                        "tool_name": tool_name,
                        "success": result.success,
                        "output": result.output,
                        "error": result.error,
                    })
                    if result.requires_user_input:
                        requires_user_input = True
                except Exception as e:
                    logger.error(f"工具执行失败: {tool_name} - {e}", exc_info=True)
                    tool_results.append({
                        "tool_call_id": tool_call_id,
                        "tool_name": tool_name,
                        "success": False,
                        "error": str(e),
                    })

            accumulated_tool_results.extend(tool_results)

            conversation.append({
                "role": "assistant",
                "content": content,
                "tool_calls": [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": json.dumps(tc["arguments"], ensure_ascii=False),
                        },
                    }
                    for tc in tool_calls
                ],
            })

            for tr in tool_results:
                conversation.append({
                    "role": "tool",
                    "tool_call_id": tr["tool_call_id"],
                    "content": json.dumps(
                        tr.get("output") or {"error": tr.get("error")},
                        ensure_ascii=False,
                    ),
                })

            if requires_user_input:
                return AgentResult(
                    message="请填写以下信息：",
                    options=[],
                    tool_results=accumulated_tool_results,
                )

            iteration += 1

        return AgentResult(
            message="抱歉，我需要更多步骤来完成这个任务。请简化一下需求。",
            options=[],
            tool_results=accumulated_tool_results,
        )

    def _build_system_prompt(self) -> str:
        if self.system_prompt:
            tools_desc = "\n".join(
                f"- **{name}**" for name in self.tools.list_tools()
            )
            return self.system_prompt.replace("{tool_descriptions}", tools_desc)
        tool_descriptions = "\n".join(
            f"- **{name}**: {tool.description[:80]}"
            for name, tool in self.tools.tools.items()
        )
        return DEFAULT_SYSTEM_PROMPT.replace("{tool_descriptions}", tool_descriptions)

    def _build_conversation(
        self, user_message: str, history: List[Dict], context: Dict
    ) -> List[Dict]:
        user_content = user_message

        if context.get("uploaded_file"):
            file_info = context["uploaded_file"]
            filename = file_info.get("original_filename") or file_info.get("filename", "")
            file_content = file_info.get("content") or {}
            if file_content.get("success"):
                full_text = file_content.get("full_text", "")
                preview = full_text[:1000] if len(full_text) > 1000 else full_text
                user_content = (
                    f"{user_message}\n\n"
                    f"[用户上传了文件: {filename}]\n"
                    f"文件内容预览:\n{preview}\n\n"
                    f"请基于此文件内容回答用户问题。"
                )

        if context.get("form_values"):
            user_content = (
                f"{user_content}\n\n"
                f"[用户提交的表单数据: {json.dumps(context['form_values'], ensure_ascii=False)}]"
            )

        messages: List[Dict] = []
        history = history[-20:]  # 保留最近20条避免 token 膨胀
        for h in history:
            role = h.get("role")
            content = h.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": user_content})
        return messages
