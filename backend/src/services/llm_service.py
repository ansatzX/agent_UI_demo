"""LLM 服务（扩展通用框架，增加合同领域方法）"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

from ..agent_framework.llm import LLMService as BaseLLMService
from ..config import settings

logger = logging.getLogger(__name__)


class LLMService(BaseLLMService):
    """扩展 LLM 服务（增加合同审查、模板分析等领域方法）"""

    def __init__(self):
        model = settings.llm_model
        api_key = self._get_api_key(model)
        api_base = self._get_api_base(model)
        super().__init__(model=model, api_key=api_key, api_base=api_base)
        if model.startswith("volcengine/") and api_key:
            os.environ["OPENAI_API_KEY"] = api_key

    def _get_api_key(self, model: str) -> Optional[str]:
        if model.startswith("deepseek/"):
            return settings.deepseek_api_key or os.getenv("DEEPSEEK_API_KEY")
        elif model.startswith("volcengine_coding_plan/"):
            return (
                settings.get_provider_api_key("volcengine_coding_plan")
                or os.getenv("VOLC_CODING_PLAN_API_KEY")
                or os.getenv("OPENAI_API_KEY")
            )
        elif model.startswith("volcengine/") or model.startswith("doubao/"):
            return (
                settings.volc_api_key
                or os.getenv("VOLC_API_KEY")
                or os.getenv("OPENAI_API_KEY")
            )
        elif model.startswith("anthropic/"):
            return settings.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        return None

    def _get_api_base(self, model: str) -> Optional[str]:
        if model.startswith("deepseek/"):
            return settings.deepseek_base_url or os.getenv("DEEPSEEK_BASE_URL")
        elif model.startswith("volcengine_coding_plan/"):
            return settings.get_provider_api_base("volcengine_coding_plan") or os.getenv(
                "VOLC_CODING_PLAN_BASE_URL"
            )
        elif model.startswith("volcengine/") or model.startswith("doubao/"):
            return settings.volc_base_url or os.getenv("VOLC_BASE_URL")
        elif model.startswith("anthropic/"):
            return settings.anthropic_base_url or os.getenv("ANTHROPIC_BASE_URL")
        return None

    def _get_litellm_params(self, messages, max_tokens=1024):
        return super()._get_litellm_params(messages, max_tokens)

    async def analyze_template(self, text_content: str) -> List[Dict[str, Any]]:
        """分析合同模板，提取可填字段"""
        try:
            prompt = f"""你是一个合同模板分析专家。请分析以下合同文本，识别出所有需要填写的字段。

合同文本：
{text_content}

请以JSON格式返回字段列表，每个字段包含：
- name: 字段标识（英文，使用下划线）
- label: 字段显示名称（中文）
- field_type: 字段类型（text, number, date, select, textarea）
- group: 分组名称
- placeholder: 填写提示（可选）
- required: 是否必填（true/false）

只返回JSON数组，不要其他文字。"""

            params = self._get_litellm_params(
                messages=[{"role": "user", "content": prompt}], max_tokens=2048
            )
            response = await self._call_llm_with_retry(params)
            content = response.choices[0].message.content
            json_start = content.find("[")
            json_end = content.rfind("]") + 1
            if json_start >= 0 and json_end > json_start:
                return json.loads(content[json_start:json_end])
            return []
        except Exception as e:
            logger.error(f"模板分析失败: {e}", exc_info=True)
            return []

    async def review_contract(self, text_content: str) -> Dict[str, Any]:
        """审查合同风险"""
        try:
            prompt = f"""你是一个合同风险审查专家。请分析以下合同文本，识别潜在的风险点。

合同文本：
{text_content}

请以JSON格式返回审查结果：
{{
  "summary": "总体评价",
  "issues": [
    {{"level": "high|medium|low", "title": "风险标题", "description": "风险描述", "suggestion": "修改建议"}}
  ]
}}
只返回JSON，不要其他文字。"""

            params = self._get_litellm_params(
                messages=[{"role": "user", "content": prompt}], max_tokens=2048
            )
            response = await self._call_llm_with_retry(params)
            content = response.choices[0].message.content
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                return json.loads(content[json_start:json_end])
            return {"summary": "无法解析审查结果", "issues": []}
        except Exception as e:
            logger.error(f"合同审查失败: {e}", exc_info=True)
            return {"summary": "审查失败", "issues": []}

    async def generate_agent_response(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]],
        contract_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """生成 Agent 响应（旧版 Option-based 接口，兼容保留）"""
        try:
            context_parts = []
            if contract_context:
                if "filename" in contract_context:
                    original_name = contract_context.get("original_filename", contract_context["filename"])
                    context_parts.append(f"用户最近上传的文件: {original_name}")
                    context_parts.append(f"文件包含 {contract_context['paragraphs_count']} 个段落和 {contract_context['tables_count']} 个表格")
                    if contract_context.get("total_files", 1) > 1:
                        context_parts.append(f"会话中共上传了 {contract_context['total_files']} 个文件")
                    context_parts.append(f"最新文件内容预览:\n{contract_context['content_preview']}")
                else:
                    context_parts.append(f"当前合同: {contract_context.get('name', '未命名')}")
                    context_parts.append(f"合同状态: {contract_context.get('status', 'draft')}")

            system_prompt = """你是一个友好的企业合同智能助手，专门帮助用户处理合同相关工作。

你的职责：
1. 理解用户的意图，提供专业的帮助
2. 主动提供下一步操作建议
3. 回答关于合同流程的问题
4. 用简洁、友好的中文回复

每次回复后，提供2-4个操作选项供用户选择。
可用action类型：select_template, upload_template, create_contract, fill_contract, review_contract, explain_process, save_draft, download_contract, analyze_contract

请以JSON格式返回你的回复：
{"message": "回复文本", "options": [{"id": "opt1", "label": "标题", "description": "说明", "action": "action_type"}]}"""

            messages = [{"role": "system", "content": system_prompt}]
            for msg in conversation_history[-5:]:
                messages.append({"role": msg["role"], "content": msg["content"]})

            if context_parts:
                user_content = f"上下文信息：\n{chr(10).join(context_parts)}\n\n用户消息：{user_message}"
            else:
                user_content = user_message
            messages.append({"role": "user", "content": user_content})

            params = self._get_litellm_params(messages=messages, max_tokens=1024)
            response = await self._call_llm_with_retry(params)

            content = response.choices[0].message.content
            token_usage = {}
            if hasattr(response, "usage") and response.usage:
                token_usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }

            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                result = json.loads(content[json_start:json_end])
                result["token_usage"] = token_usage
                if not result.get("message") or not result["message"].strip():
                    result["message"] = "抱歉，我暂时无法处理这个请求。"
                return result

            return {
                "message": content if content.strip() else "抱歉，我暂时无法处理这个请求。",
                "options": [],
                "token_usage": token_usage,
            }
        except Exception as e:
            logger.error(f"生成Agent响应失败: {e}", exc_info=True)
            return {"message": "抱歉，处理您的请求时出现错误。", "options": [], "token_usage": {}}
