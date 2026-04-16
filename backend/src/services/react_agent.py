# backend/src/services/react_agent.py
import json
import logging
from typing import Dict, Any, List
from dataclasses import dataclass, field
from .llm_service import LLMService
from .tool_registry import ToolRegistry

logger = logging.getLogger(__name__)

@dataclass
class AgentResult:
    """Agent 的最终结果"""
    message: str
    options: List[Dict] = field(default_factory=list)
    tool_calls: List[Dict] = field(default_factory=list)
    tool_results: List[Dict] = field(default_factory=list)

class ReActAgent:
    """基于原生 function calling 的 ReAct Agent"""

    def __init__(
        self,
        llm_service: LLMService,
        tool_registry: ToolRegistry,
        max_iterations: int = 10
    ):
        self.llm = llm_service
        self.tools = tool_registry
        self.max_iterations = max_iterations

    async def run(
        self,
        user_message: str,
        context: Dict,
        history: List[Dict] = None
    ) -> AgentResult:
        """
        执行 ReAct 循环：思考 → 行动 → 观察 → 重复

        使用 OpenAI 原生 function calling

        history: 之前会话中的消息列表 [{"role": "user"|"assistant", "content": "..."}]
        """
        iteration = 0
        conversation = self._build_conversation(user_message, history or [], context)
        # 累积所有轮次的工具执行结果，供最终返回使用
        accumulated_tool_results: List[Dict] = []

        while iteration < self.max_iterations:
            # 1. 思考：LLM 决定是否调用工具
            system_prompt = self._build_system_prompt()
            response = await self.llm.generate_react_response(
                system_prompt=system_prompt,
                conversation=conversation,
                tools=self.tools.get_tool_definitions()
            )

            content = response.get("content", "")
            tool_calls = response.get("tool_calls", [])

            logger.info(f"ReAct Agent 第 {iteration + 1} 轮: tool_calls={len(tool_calls)}")

            # 2. 如果没有工具调用，直接回复用户（带上之前累积的工具结果）
            if not tool_calls:
                return AgentResult(
                    message=content,
                    options=[],
                    tool_results=accumulated_tool_results
                )

            # 3. 执行所有工具调用
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
                        "error": result.error
                    })

                    # 如果需要用户输入，立即返回
                    if result.requires_user_input:
                        requires_user_input = True

                except Exception as e:
                    logger.error(f"工具执行失败: {tool_name} - {e}", exc_info=True)
                    tool_results.append({
                        "tool_call_id": tool_call_id,
                        "tool_name": tool_name,
                        "success": False,
                        "error": str(e)
                    })

            accumulated_tool_results.extend(tool_results)

            # 4. 把 assistant 消息和 tool 结果加回 conversation
            conversation.append({
                "role": "assistant",
                "content": content,
                "tool_calls": [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": json.dumps(tc["arguments"], ensure_ascii=False)
                        }
                    }
                    for tc in tool_calls
                ]
            })

            for tr in tool_results:
                conversation.append({
                    "role": "tool",
                    "tool_call_id": tr["tool_call_id"],
                    "content": json.dumps(tr.get("output") or {"error": tr.get("error")}, ensure_ascii=False)
                })

            # 5. 如果需要用户输入，暂停循环（返回累积的结果）
            if requires_user_input:
                return AgentResult(
                    message="请填写以下信息：",
                    options=[],
                    tool_results=accumulated_tool_results
                )

            iteration += 1

        # 超过最大迭代次数
        return AgentResult(
            message="抱歉，我需要更多步骤来完成这个任务。请简化一下需求。",
            options=[],
            tool_results=accumulated_tool_results
        )

    def _build_system_prompt(self) -> str:
        """构建系统提示"""
        return """你是一个智能合同助手。你可以使用工具来帮助用户完成合同生成流程。

**核心流程：**
1. 用户上传模板后（用户消息会包含文件内容摘要和"模板文件名"字段），**不要再调用 read_file**，直接从摘要里识别 {{占位符}}。
2. 当用户表达"帮我填写/生成合同"等意图时，**立即调用 show_form**，把占位符作为字段列表。
3. 用户提交表单数据后（消息里会有"用户提交的表单数据"），**立即调用 generate_document** 生成文档：
   - `template_filename` 使用用户消息里的"模板文件名"字段值（唯一文件名，如 20260417_xxxxx_合同模板.docx）
   - `fields` 使用用户提交的表单数据
   - `filename` 给一个合理的输出名，例如 "填写完成的合同.docx"

**可用工具：**
- show_form: 向用户显示动态表单，收集占位符字段
- generate_document: 基于上传的模板生成填好的合同文档
- read_file: 仅当用户显式要求读取某个文本文件时使用，**不要**用它读模板（模板内容已在消息里提供）

**规则：**
- 不要编造 template_id 或 template_filename；必须从用户消息里"模板文件名"字段取值
- 工具参数必须严格符合 JSON Schema
- 当已经拿到了表单数据和模板文件名时，不要再犹豫，直接调用 generate_document
"""

    def _build_conversation(
        self,
        user_message: str,
        history: List[Dict],
        context: Dict
    ) -> List[Dict]:
        """构建对话历史"""
        # 构建用户消息，包含文件上下文
        user_content = user_message

        if context.get("uploaded_file"):
            file_info = context["uploaded_file"]
            unique_filename = file_info.get("filename", "")
            display_filename = file_info.get("original_filename") or unique_filename or "未知文件"
            file_content = file_info.get("content") or {}

            # 如果文件解析成功，包含实际内容
            if file_content and file_content.get("success"):
                paragraphs = file_content.get("paragraphs") or []
                tables = file_content.get("tables") or []
                full_text = file_content.get("full_text") or ""

                # 构建文件摘要（限制长度避免 token 过多）
                preview_text = full_text[:1000] if len(full_text) > 1000 else full_text

                user_content = (
                    f"{user_message}\n\n"
                    f"[用户上传了文件: {display_filename}]\n"
                    f"模板文件名（调用 generate_document 时使用）: {unique_filename}\n"
                    f"文件内容摘要：\n- 段落数: {len(paragraphs)}\n- 表格数: {len(tables)}\n- 总字符数: {len(full_text)}\n\n"
                    f"前1000字符预览:\n{preview_text}\n\n"
                    f"请基于此文件内容回答用户问题。"
                )
                logger.info(f"Agent 收到文件: {display_filename} (unique={unique_filename})")
            else:
                # 文件解析失败
                error = file_content.get("error", "未知错误") if file_content else "文件内容未加载"
                user_content = f"{user_message}\n\n[用户上传了文件: {display_filename}，但解析失败: {error}]"
                logger.warning(f"Agent 收到文件: {display_filename}，但解析失败: {error}")

        if context.get("form_values"):
            user_content = f"{user_content}\n\n[用户提交的表单数据: {json.dumps(context['form_values'], ensure_ascii=False)}]"

        # 构建对话历史：先放历史消息，再放当前用户消息
        messages: List[Dict] = []
        for h in history:
            role = h.get("role")
            content = h.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": user_content})

        return messages
