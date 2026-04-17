"""ReAct (Reasoning and Acting) agent implementation.

This module provides a ReAct agent that uses native function calling
to reason about user requests and execute tools in a loop until
a final response is generated.

Classes:
    AgentResult: Data class for agent execution results.
    ReActAgent: Main agent class for tool-based interactions.

Example:
    >>> from backend.src.services.react_agent import ReActAgent
    >>> agent = ReActAgent(llm_service, tool_registry)
    >>> result = await agent.run("Generate a contract", context, history)
"""

import asyncio
from dataclasses import dataclass
from dataclasses import field
import json
import logging
from typing import Any, Dict, List

from .llm_service import LLMService
from .tool_registry import ToolRegistry

logger = logging.getLogger(__name__)


@dataclass
class AgentResult:
    """Agent execution result container.

    Attributes:
        message: Final response message to the user.
        options: List of suggested next actions (optional).
        tool_calls: List of tool calls made during execution (optional).
        tool_results: List of tool execution results (optional).
    """

    message: str
    options: List[Dict] = field(default_factory=list)
    tool_calls: List[Dict] = field(default_factory=list)
    tool_results: List[Dict] = field(default_factory=list)


class ReActAgent:
    """ReAct agent using native function calling.

    Implements a Reasoning and Acting loop where the agent reasons
    about the user's request, executes tools, observes results,
    and repeats until generating a final response.

    Attributes:
        llm: LLM service for generating responses.
        tools: Tool registry for executing actions.
        max_iterations: Maximum number of reasoning iterations.
        timeout: Total execution timeout in seconds.
    """

    def __init__(
        self,
        llm_service: LLMService,
        tool_registry: ToolRegistry,
        max_iterations: int = 10,
        timeout: int = 300,
    ):
        """Initialize ReActAgent.

        Args:
            llm_service: LLM service for generating responses.
            tool_registry: Registry of available tools.
            max_iterations: Maximum reasoning iterations (default: 10).
            timeout: Total execution timeout in seconds (default: 300).
        """
        self.llm = llm_service
        self.tools = tool_registry
        self.max_iterations = max_iterations
        self.timeout = timeout

    async def run(
        self, user_message: str, context: Dict, history: List[Dict] = None
    ) -> AgentResult:
        """
        执行 ReAct 循环：思考 → 行动 → 观察 → 重复（带总超时）

        使用 OpenAI 原生 function calling

        history: 之前会话中的消息列表 [{"role": "user"|"assistant", "content": "..."}]
        """
        try:
            # 使用 asyncio.wait_for 控制总超时
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
        """ReAct 循环实现"""
        iteration = 0
        conversation = self._build_conversation(
            user_message, history or [], context
        )
        # 累积所有轮次的工具执行结果，供最终返回使用
        accumulated_tool_results: List[Dict] = []

        while iteration < self.max_iterations:
            # 1. 思考：LLM 决定是否调用工具
            system_prompt = self._build_system_prompt()
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

            # 2. 如果没有工具调用，直接回复用户（带上之前累积的工具结果）
            if not tool_calls:
                return AgentResult(
                    message=content,
                    options=[],
                    tool_results=accumulated_tool_results,
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

                    tool_results.append(
                        {
                            "tool_call_id": tool_call_id,
                            "tool_name": tool_name,
                            "success": result.success,
                            "output": result.output,
                            "error": result.error,
                        }
                    )

                    # 如果需要用户输入，立即返回
                    if result.requires_user_input:
                        requires_user_input = True

                except Exception as e:
                    logger.error(
                        f"工具执行失败: {tool_name} - {e}", exc_info=True
                    )
                    tool_results.append(
                        {
                            "tool_call_id": tool_call_id,
                            "tool_name": tool_name,
                            "success": False,
                            "error": str(e),
                        }
                    )

            accumulated_tool_results.extend(tool_results)

            # 4. 把 assistant 消息和 tool 结果加回 conversation
            conversation.append(
                {
                    "role": "assistant",
                    "content": content,
                    "tool_calls": [
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": {
                                "name": tc["name"],
                                "arguments": json.dumps(
                                    tc["arguments"], ensure_ascii=False
                                ),
                            },
                        }
                        for tc in tool_calls
                    ],
                }
            )

            for tr in tool_results:
                conversation.append(
                    {
                        "role": "tool",
                        "tool_call_id": tr["tool_call_id"],
                        "content": json.dumps(
                            tr.get("output") or {"error": tr.get("error")},
                            ensure_ascii=False,
                        ),
                    }
                )

            # 5. 如果需要用户输入，暂停循环（返回累积的结果）
            if requires_user_input:
                return AgentResult(
                    message="请填写以下信息：",
                    options=[],
                    tool_results=accumulated_tool_results,
                )

            iteration += 1

        # 超过最大迭代次数
        return AgentResult(
            message="抱歉，我需要更多步骤来完成这个任务。请简化一下需求。",
            options=[],
            tool_results=accumulated_tool_results,
        )

    def _build_system_prompt(self) -> str:
        """构建系统提示"""
        return """你是一个智能助手，具备合同生成和智能写作两大核心能力。

## 合同生成场景

**触发条件**：用户上传 .docx 模板或表达"签订合同"、"填写合同"等意图

**核心流程**：
1. 用户上传模板后，从摘要里识别 {{占位符}}
2. 调用 show_form 工具，将占位符转为表单字段
3. 用户提交表单数据后，调用 generate_document 生成合同文档：
   - `template_filename` 从用户消息里"模板文件名"字段取值
   - `fields` 使用用户提交的表单数据
   - `filename` 给合理的输出名（如"合同.docx"）
4. 生成完成后，主动询问是否需要其他帮助：
   - "您是否需要了解合同审批流程？"
   - "是否需要我为您填充合同？"
   - "是否需要合同签署、立项、资金到账等流程的解释？"

## 智能写作场景

**触发条件**：用户表达"写报告"、"写新闻稿"、"写公众号文章"、"总结项目"等写作需求

**核心流程**：
1. **收集素材**：
   - 如果用户提供 URL，调用 read_webpage 爬取网页内容
   - 如果用户上传文档，从消息里提取文件内容
   - 如果用户直接提供信息，直接使用
   - 必要时通过表单收集更多信息

2. **调用 write_article 工具**：
   - `article_type`: project_report（项目报告）, news_release（新闻稿）, wechat_article（公众号推文）, general（通用文章）
   - `topic`: 文章主题或标题
   - `style`: formal（正式）, casual（轻松）, academic（学术）, lively（活泼）
   - `source_material`: 从步骤1收集的素材
   - `output_format`: markdown（推荐）或 text

3. **生成并展示内容**：
   - 工具会返回结构模板和风格指南
   - 你需要根据模板、风格和素材，生成完整的文章内容（Markdown 格式）
   - **直接将内容展示给用户**，询问是否需要生成 Word 文档
   - 如果是 slide_outline，生成幻灯片大纲（每页标题 + 要点）

4. **生成 Word 文档（按需）**：
   - 当用户明确要求生成 Word 文档或下载文档时，调用 save_document 工具
   - `title`: 文档标题
   - `content`: 步骤3生成的完整内容
   - `document_type`: 文档类型（如"项目报告"、"新闻稿"等）
   - 返回下载链接供用户下载

**示例对话**：
- 用户："我要写一个关于产研合作活动的新闻稿，这是我们活动的介绍：XXX"
- 你：
  1. 调用 write_article(article_type="news_release", topic="产研合作活动新闻稿", source_material="XXX", style="formal")
  2. 根据返回的结构模板，撰写正式风格的新闻稿内容
  3. 展示完整内容给用户
  4. 询问："我已经为您生成了新闻稿内容，是否需要我将它保存为 Word 文档供您下载？"

- 用户："帮我写一个项目总结报告，参考这个网页：https://example.com/project"
- 你：
  1. 调用 read_webpage(url="https://example.com/project") 获取内容
  2. 调用 write_article(article_type="project_report", topic="项目总结报告", source_material=<网页内容>, style="academic")
  3. 根据结构模板撰写学术风格的项目报告
  4. 展示完整内容给用户
  5. 询问："报告已经生成完毕，您需要我将它导出为 Word 文档吗？"

- 用户："生成 Word 文档"
- 你：调用 save_document(title="项目总结报告", content=<之前生成的报告内容>, document_type="项目报告")

## 可用工具

- **show_form**: 向用户显示动态表单
- **generate_document**: 基于模板生成合同文档
- **read_file**: 读取本地文件内容
- **read_webpage**: 爬取网页内容
- **write_article**: 根据主题和素材生成文章结构和风格指南
- **save_document**: 将生成的内容保存为 Word 文档（.docx）

## 核心规则

1. **识别意图**：优先判断用户需求属于合同生成还是智能写作
2. **主动引导**：完成当前任务后，主动询问下一步需求（如豆包一样）
3. **工具参数**：严格遵循 JSON Schema，不编造不存在的参数
4. **内容生成**：调用 write_article 后，必须生成完整的文章内容并展示给用户
5. **按需生成文档**：**只有当用户明确要求生成 Word 文档时才调用 save_document**
6. **幻灯片格式**：当 output_format="slide_outline" 时，生成：
   ```
   # Slide 1: 标题
   - 要点1
   - 要点2

   # Slide 2: 标题
   - 要点1
   ```
"""

    def _build_conversation(
        self, user_message: str, history: List[Dict], context: Dict
    ) -> List[Dict]:
        """构建对话历史"""
        # 构建用户消息，包含文件上下文
        user_content = user_message

        if context.get("uploaded_file"):
            file_info = context["uploaded_file"]
            unique_filename = file_info.get("filename", "")
            display_filename = (
                file_info.get("original_filename")
                or unique_filename
                or "未知文件"
            )
            file_content = file_info.get("content") or {}

            # 如果文件解析成功，包含实际内容
            if file_content and file_content.get("success"):
                paragraphs = file_content.get("paragraphs") or []
                tables = file_content.get("tables") or []
                full_text = file_content.get("full_text") or ""

                # 构建文件摘要（限制长度避免 token 过多）
                preview_text = (
                    full_text[:1000] if len(full_text) > 1000 else full_text
                )

                user_content = (
                    f"{user_message}\n\n"
                    f"[用户上传了文件: {display_filename}]\n"
                    f"模板文件名（调用 generate_document 时使用）: {unique_filename}\n"
                    f"文件内容摘要：\n- 段落数: {len(paragraphs)}\n- 表格数: {len(tables)}\n- 总字符数: {len(full_text)}\n\n"
                    f"前1000字符预览:\n{preview_text}\n\n"
                    f"请基于此文件内容回答用户问题。"
                )
                logger.info(
                    f"Agent 收到文件: {display_filename} (unique={unique_filename})"
                )
            else:
                # 文件解析失败
                error = (
                    file_content.get("error", "未知错误")
                    if file_content
                    else "文件内容未加载"
                )
                user_content = f"{user_message}\n\n[用户上传了文件: {display_filename}，但解析失败: {error}]"
                logger.warning(
                    f"Agent 收到文件: {display_filename}，但解析失败: {error}"
                )

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
