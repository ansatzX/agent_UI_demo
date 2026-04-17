"""LLM service integration with retry and timeout handling.

This module provides a unified interface for interacting with various LLM
providers through LiteLLM. It includes automatic retry logic, timeout handling,
and support for multiple providers.

Classes:
    LLMService: Main service class for LLM operations.

Example:
    >>> from backend.src.services.llm_service import LLMService
    >>> service = LLMService()
    >>> fields = await service.analyze_template(text_content)
"""

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional

from litellm import acompletion
from tenacity import retry
from tenacity import retry_if_exception_type
from tenacity import stop_after_attempt
from tenacity import wait_exponential

from ..config import settings

logger = logging.getLogger(__name__)


class LLMService:
    """Service for LLM operations with built-in retry and timeout handling.

    This service provides a unified interface for LLM operations including
    template analysis, agent response generation, and contract review.
    It automatically handles retries with exponential backoff and timeouts.

    Attributes:
        model: Default LLM model identifier.
        api_key: API key for the current provider.
        api_base: Base URL for the current provider API.
        timeout: Timeout in seconds for LLM API calls (default: 60).
        max_retries: Maximum number of retry attempts (default: 3).
    """

    def __init__(self):
        """Initialize LLMService with configuration from settings."""
        self.model = settings.llm_model
        self.api_key = self._get_api_key()
        self.api_base = self._get_api_base()
        self.timeout = 60  # seconds
        self.max_retries = 3

    def _get_api_key(self) -> Optional[str]:
        """Select appropriate API key based on model prefix.

        Automatically determines the correct API key by checking the
        model identifier prefix and matching it with the corresponding
        provider configuration.

        Returns:
            API key string if found, None otherwise.
        """
        if self.model.startswith("deepseek/"):
            return settings.deepseek_api_key or os.getenv("DEEPSEEK_API_KEY")
        elif self.model.startswith("volcengine_coding_plan/"):
            # 火山引擎编码计划专用endpoint
            return (
                settings.get_provider_api_key("volcengine_coding_plan")
                or os.getenv("VOLC_CODING_PLAN_API_KEY")
                or os.getenv("OPENAI_API_KEY")
            )
        elif self.model.startswith("volcengine/") or self.model.startswith(
            "doubao/"
        ):
            # Volcano Engine LiteLLM uses OPENAI_API_KEY
            return (
                settings.volc_api_key
                or os.getenv("VOLC_API_KEY")
                or os.getenv("OPENAI_API_KEY")
            )
        elif self.model.startswith("anthropic/"):
            return settings.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        return None

    def _get_api_base(self) -> Optional[str]:
        """Select appropriate API base URL based on model prefix.

        Automatically determines the correct API base URL by checking
        the model identifier prefix and matching it with the corresponding
        provider configuration.

        Returns:
            API base URL string if found, None otherwise.
        """
        if self.model.startswith("deepseek/"):
            return settings.deepseek_base_url or os.getenv("DEEPSEEK_BASE_URL")
        elif self.model.startswith("volcengine_coding_plan/"):
            # 火山引擎编码计划专用endpoint
            return settings.get_provider_api_base(
                "volcengine_coding_plan"
            ) or os.getenv("VOLC_CODING_PLAN_BASE_URL")
        elif self.model.startswith("volcengine/") or self.model.startswith(
            "doubao/"
        ):
            return settings.volc_base_url or os.getenv("VOLC_BASE_URL")
        elif self.model.startswith("anthropic/"):
            return settings.anthropic_base_url or os.getenv(
                "ANTHROPIC_BASE_URL"
            )
        return None

    def _get_litellm_model(self) -> str:
        """Get LiteLLM-compatible model name.

        Converts provider-specific model names to LiteLLM-compatible format.

        Returns:
            Model name string compatible with LiteLLM.
        """
        # volcengine_coding_plan uses volcengine prefix
        if self.model.startswith("volcengine_coding_plan/"):
            return self.model.replace("volcengine_coding_plan/", "volcengine/")
        return self.model

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((TimeoutError, ConnectionError)),
    )
    async def _call_llm_with_retry(self, params: Dict) -> Any:
        """Call LLM API with retry logic and timeout handling.

        Makes an LLM API call with automatic retry on timeout or connection
        errors. Uses exponential backoff for retries.

        Args:
            params: Dictionary of parameters for LLM API call.

        Returns:
            LLM API response object.

        Raises:
            TimeoutError: If API call times out after retries.
            Exception: If API call fails after all retry attempts.
        """
        try:
            # Add timeout control
            response = await asyncio.wait_for(
                acompletion(**params), timeout=self.timeout
            )
            return response
        except asyncio.TimeoutError:
            logger.error(f"LLM call timeout ({self.timeout}s)")
            raise TimeoutError(f"LLM call timeout")
        except Exception as e:
            logger.error(f"LLM call failed: {e}", exc_info=True)
            raise

    def _get_litellm_params(
        self, messages: List[Dict], max_tokens: int = 1024
    ) -> Dict:
        """Build parameters for LiteLLM API call.

        Constructs a parameter dictionary ready for LiteLLM API calls,
        including model, messages, API credentials, and other settings.

        Args:
            messages: List of message dictionaries for the conversation.
            max_tokens: Maximum tokens for the response (default: 1024).

        Returns:
            Dictionary of parameters ready for LiteLLM API call.
        """
        # Volcano Engine requires OPENAI_API_KEY environment variable
        if self.model.startswith("volcengine/") and self.api_key:
            os.environ["OPENAI_API_KEY"] = self.api_key

        params = {
            "model": self._get_litellm_model(),
            "messages": messages,
            "max_tokens": max_tokens,
        }
        if self.api_key:
            params["api_key"] = self.api_key
        if self.api_base:
            params["api_base"] = self.api_base
        return params

    async def analyze_template(self, text_content: str) -> List[Dict[str, Any]]:
        """Analyze contract template to extract fillable fields.

        Uses LLM to identify all placeholder fields in a contract template
        that need to be filled by the user.

        Args:
            text_content: Full text content of the contract template.

        Returns:
            List of field dictionaries, where each dictionary contains:
                - name: Field identifier in snake_case (str).
                - label: Display name in Chinese (str).
                - field_type: Type of field ('text', 'number', 'date',
                  'select', 'textarea').
                - group: Group name for organization (str, optional).
                - placeholder: Hint text for user input (str, optional).
                - required: Whether field is mandatory (bool).
            Returns empty list if analysis fails.

        Raises:
            No exceptions are raised; errors are logged instead.
        """
        try:
            prompt = f"""你是一个合同模板分析专家。请分析以下合同文本，识别出所有需要填写的字段。

合同文本：
{text_content}

请以JSON格式返回字段列表，每个字段包含：
- name: 字段标识（英文，使用下划线）
- label: 字段显示名称（中文）
- field_type: 字段类型（text, number, date, select, textarea）
- group: 分组名称（如"甲方信息"、"乙方信息"、"货物信息"等）
- placeholder: 填写提示（可选）
- required: 是否必填（true/false）

只返回JSON数组，不要其他文字。"""

            params = self._get_litellm_params(
                messages=[{"role": "user", "content": prompt}], max_tokens=2048
            )
            response = await self._call_llm_with_retry(params)

            content = response.choices[0].message.content
            try:
                json_start = content.find("[")
                json_end = content.rfind("]") + 1
                if json_start >= 0 and json_end > json_start:
                    return json.loads(content[json_start:json_end])
                return []
            except json.JSONDecodeError as e:
                logger.error(
                    "JSON解析失败",
                    extra={
                        "error": str(e),
                        "content_preview": content[:200],
                        "position": e.pos,
                        "line": e.lineno,
                        "column": e.colno,
                    },
                )
                return []
        except Exception as e:
            logger.error(f"模板分析失败: {e}", exc_info=True)
            return []

    async def generate_agent_response(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]],
        contract_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate agent response for user message.

        Creates a context-aware response to user messages using conversation
        history and contract context.

        Args:
            user_message: The user's input message.
            conversation_history: List of previous messages, each with
                'role' and 'content' keys.
            contract_context: Optional context about uploaded files or
                current contract state.

        Returns:
            Dictionary containing:
                - message: Agent's response text (str).
                - options: List of suggested next actions (list of dicts).
                - token_usage: Token usage statistics (dict).
            Returns error message dict if generation fails.

        Raises:
            No exceptions are raised; errors are logged instead.
        """
        try:
            context_parts = []

            # 处理文件上下文
            if contract_context:
                if "filename" in contract_context:
                    # 这是文件上下文
                    original_name = contract_context.get(
                        "original_filename", contract_context["filename"]
                    )
                    context_parts.append(f"用户最近上传的文件: {original_name}")
                    context_parts.append(
                        f"文件包含 {contract_context['paragraphs_count']} 个段落和 {contract_context['tables_count']} 个表格"
                    )

                    # 如果有多个文件，告诉LLM
                    if contract_context.get("total_files", 1) > 1:
                        context_parts.append(
                            f"注意：此会话中总共上传了 {contract_context['total_files']} 个文件"
                        )

                    context_parts.append(
                        f"最新文件内容预览:\n{contract_context['content_preview']}"
                    )
                else:
                    # 这是合同上下文
                    context_parts.append(
                        f"当前合同: {contract_context.get('name', '未命名')}"
                    )
                    context_parts.append(
                        f"合同状态: {contract_context.get('status', 'draft')}"
                    )

            system_prompt = """你是一个友好的企业合同智能助手，专门帮助用户处理合同相关工作。

你的职责：
1. 理解用户的意图，提供专业的帮助
2. 主动提供下一步操作建议
3. 回答关于合同流程的问题
4. 用简洁、友好的中文回复
5. 如果用户上传了合同文件，主动分析合同内容并提供帮助

每次回复后，提供2-4个操作选项供用户选择。
选项格式：每个选项包含id, label（简短标题）, description（详细说明）, action（操作类型）。

可用的action类型：
- select_template: 选择模板
- upload_template: 上传模板
- create_contract: 创建合同
- fill_contract: 填充合同
- review_contract: 审查合同
- explain_process: 解释流程
- save_draft: 保存草稿
- download_contract: 下载合同
- analyze_contract: 分析合同

请以JSON格式返回你的回复，格式如下：
{
  "message": "你的回复文本",
  "options": [
    {"id": "opt1", "label": "选项标题", "description": "选项说明", "action": "action_type"}
  ]
}"""

            messages = [{"role": "system", "content": system_prompt}]
            for msg in conversation_history[-5:]:
                messages.append(
                    {"role": msg["role"], "content": msg["content"]}
                )

            if context_parts:
                user_content = f"上下文信息：\n{'\n'.join(context_parts)}\n\n用户消息：{user_message}"
            else:
                user_content = user_message

            messages.append({"role": "user", "content": user_content})

            params = self._get_litellm_params(
                messages=messages, max_tokens=1024
            )
            response = await self._call_llm_with_retry(params)

            content = response.choices[0].message.content

            # 提取token使用统计
            token_usage = {}
            if hasattr(response, "usage"):
                token_usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }

            try:
                json_start = content.find("{")
                json_end = content.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    result = json.loads(content[json_start:json_end])
                    result["token_usage"] = token_usage

                    # 确保message字段不为空
                    if (
                        not result.get("message")
                        or not result["message"].strip()
                    ):
                        result["message"] = (
                            "抱歉，我暂时无法处理这个请求。请稍后重试或换一个问题。"
                        )

                    return result
            except json.JSONDecodeError as e:
                logger.error(
                    "JSON解析失败",
                    extra={
                        "error": str(e),
                        "content_preview": content[:200],
                        "position": e.pos,
                        "line": e.lineno,
                        "column": e.colno,
                    },
                )

            return {
                "message": (
                    content
                    if content and content.strip()
                    else "抱歉，我暂时无法处理这个请求。请稍后重试。"
                ),
                "options": [],
                "token_usage": token_usage,
            }
        except Exception as e:
            logger.error(f"生成Agent响应失败: {e}", exc_info=True)
            return {
                "message": "抱歉，处理您的请求时出现错误，请稍后重试。",
                "options": [],
                "token_usage": {},
            }

    async def review_contract(self, text_content: str) -> Dict[str, Any]:
        """Review contract for potential risks and issues.

        Analyzes contract text to identify risk factors and provides
        suggestions for improvement.

        Args:
            text_content: Full text content of the contract to review.

        Returns:
            Dictionary containing:
                - summary: Overall assessment (str).
                - issues: List of identified issues, each with level,
                  title, description, and suggestion.
            Returns error dict if review fails.

        Raises:
            No exceptions are raised; errors are logged instead.
        """
        try:
            prompt = f"""你是一个合同风险审查专家。请分析以下合同文本，识别潜在的风险点。

合同文本：
{text_content}

请以JSON格式返回审查结果，格式如下：
{{
  "summary": "总体评价",
  "issues": [
    {{
      "level": "high|medium|low",
      "title": "风险标题",
      "description": "风险描述",
      "suggestion": "修改建议"
    }}
  ]
}}

只返回JSON，不要其他文字。"""

            params = self._get_litellm_params(
                messages=[{"role": "user", "content": prompt}], max_tokens=2048
            )
            response = await self._call_llm_with_retry(params)

            content = response.choices[0].message.content
            try:
                json_start = content.find("{")
                json_end = content.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    return json.loads(content[json_start:json_end])
            except json.JSONDecodeError as e:
                logger.error(
                    "JSON解析失败",
                    extra={
                        "error": str(e),
                        "content_preview": content[:200],
                        "position": e.pos,
                        "line": e.lineno,
                        "column": e.colno,
                    },
                )

            return {"summary": "无法解析审查结果", "issues": []}
        except Exception as e:
            logger.error(f"合同审查失败: {e}", exc_info=True)
            return {"summary": "审查失败", "issues": []}

    async def generate_react_response(
        self, system_prompt: str, conversation: List[Dict], tools: List[Dict]
    ) -> Dict[str, Any]:
        """生成 ReAct 响应（原生 function calling，带异常处理）"""
        try:
            messages = [{"role": "system", "content": system_prompt}]
            messages.extend(conversation)

            params = self._get_litellm_params(
                messages=messages, max_tokens=1024
            )

            # 添加工具定义（tools 已经是 OpenAI 格式）
            params["tools"] = tools
            params["tool_choice"] = "auto"

            response = await self._call_llm_with_retry(params)
            message = response.choices[0].message

            # 返回 content + tool_calls 结构
            tool_calls = []
            if hasattr(message, "tool_calls") and message.tool_calls:
                for tc in message.tool_calls:
                    # 使用 json-repair 安全解析 JSON 参数
                    try:
                        from json_repair import repair_json

                        args_str = tc.function.arguments or "{}"

                        # 尝试直接解析
                        try:
                            arguments = json.loads(args_str)
                        except json.JSONDecodeError:
                            # 使用 json-repair 修复
                            logger.warning(
                                f"JSON 解析失败，尝试修复: {args_str[:100]}"
                            )
                            arguments = repair_json(args_str)
                            logger.info(f"JSON 修复成功")

                    except Exception as e:
                        logger.error(f"工具参数解析失败: {e}")
                        logger.error(f"原始参数: {args_str[:200]}")
                        arguments = {}

                    tool_calls.append(
                        {
                            "id": tc.id,
                            "name": tc.function.name,
                            "arguments": arguments,
                        }
                    )

            return {"content": message.content or "", "tool_calls": tool_calls}
        except Exception as e:
            logger.error(f"生成ReAct响应失败: {e}", exc_info=True)
            return {
                "content": "抱歉，处理您的请求时出现错误。",
                "tool_calls": [],
            }
