import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional

from json_repair import repair_json
from litellm import acompletion
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class LLMService:
    """通用 LLM 服务（基于 LiteLLM，支持多 Provider）"""

    def __init__(
        self,
        model: str = "",
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        timeout: int = 60,
    ):
        self.model = model
        self.api_key = api_key
        self.api_base = api_base
        self.timeout = timeout

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((TimeoutError, ConnectionError)),
    )
    async def _call_llm_with_retry(self, params: Dict) -> Any:
        try:
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
        self, messages: List[Dict], max_tokens: int = 1024, **kwargs
    ) -> Dict:
        params = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
        }
        if self.api_key:
            params["api_key"] = self.api_key
        if self.api_base:
            params["api_base"] = self.api_base
        params.update(kwargs)
        return params

    async def generate_response(
        self,
        system_prompt: str,
        messages: List[Dict],
        max_tokens: int = 1024,
    ) -> Dict[str, Any]:
        """通用对话生成"""
        try:
            full_messages = [{"role": "system", "content": system_prompt}]
            full_messages.extend(messages)

            params = self._get_litellm_params(
                messages=full_messages, max_tokens=max_tokens
            )
            response = await self._call_llm_with_retry(params)

            content = response.choices[0].message.content or ""
            token_usage = {}
            if hasattr(response, "usage") and response.usage:
                token_usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }

            return {"content": content, "token_usage": token_usage}
        except Exception as e:
            logger.error(f"生成响应失败: {e}", exc_info=True)
            return {"content": "抱歉，处理您的请求时出现错误。", "token_usage": {}}

    async def generate_react_response(
        self, system_prompt: str, conversation: List[Dict], tools: List[Dict]
    ) -> Dict[str, Any]:
        """生成 ReAct 响应（原生 function calling）"""
        try:
            messages = [{"role": "system", "content": system_prompt}]
            messages.extend(conversation)

            params = self._get_litellm_params(
                messages=messages, max_tokens=1024
            )
            params["tools"] = tools
            params["tool_choice"] = "auto"

            response = await self._call_llm_with_retry(params)
            message = response.choices[0].message

            tool_calls = []
            if hasattr(message, "tool_calls") and message.tool_calls:
                for tc in message.tool_calls:
                    try:
                        args_str = tc.function.arguments or "{}"
                        try:
                            arguments = json.loads(args_str)
                        except json.JSONDecodeError:
                            logger.warning(f"JSON 修复: {args_str[:100]}")
                            arguments = repair_json(args_str)
                    except Exception as e:
                        logger.error(f"工具参数解析失败: {e}")
                        arguments = {}

                    tool_calls.append({
                        "id": tc.id,
                        "name": tc.function.name,
                        "arguments": arguments,
                    })

            return {"content": message.content or "", "tool_calls": tool_calls}
        except Exception as e:
            logger.error(f"生成ReAct响应失败: {e}", exc_info=True)
            return {"content": "抱歉，处理您的请求时出现错误。", "tool_calls": []}
