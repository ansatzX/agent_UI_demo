from litellm import acompletion
from typing import List, Dict, Any, Optional
import json
import os
from ..config import settings


class LLMService:
    def __init__(self):
        self.model = settings.llm_model
        self.api_key = self._get_api_key()
        self.api_base = self._get_api_base()

    def _get_api_key(self) -> Optional[str]:
        """根据模型自动选择对应的API key"""
        if self.model.startswith('deepseek/'):
            return settings.deepseek_api_key or os.getenv('DEEPSEEK_API_KEY')
        elif self.model.startswith('volcengine_coding_plan/'):
            # 火山引擎编码计划专用endpoint
            return settings.get_provider_api_key('volcengine_coding_plan') or os.getenv('VOLC_CODING_PLAN_API_KEY') or os.getenv('OPENAI_API_KEY')
        elif self.model.startswith('volcengine/') or self.model.startswith('doubao/'):
            # 火山引擎LiteLLM使用OPENAI_API_KEY
            return settings.volc_api_key or os.getenv('VOLC_API_KEY') or os.getenv('OPENAI_API_KEY')
        elif self.model.startswith('anthropic/'):
            return settings.anthropic_api_key or os.getenv('ANTHROPIC_API_KEY')
        return None

    def _get_api_base(self) -> Optional[str]:
        """根据模型自动选择对应的API base url"""
        if self.model.startswith('deepseek/'):
            return settings.deepseek_base_url or os.getenv('DEEPSEEK_BASE_URL')
        elif self.model.startswith('volcengine_coding_plan/'):
            # 火山引擎编码计划专用endpoint
            return settings.get_provider_api_base('volcengine_coding_plan') or os.getenv('VOLC_CODING_PLAN_BASE_URL')
        elif self.model.startswith('volcengine/') or self.model.startswith('doubao/'):
            return settings.volc_base_url or os.getenv('VOLC_BASE_URL')
        elif self.model.startswith('anthropic/'):
            return settings.anthropic_base_url or os.getenv('ANTHROPIC_BASE_URL')
        return None

    def _get_litellm_model(self) -> str:
        """获取litellm兼容的模型名称"""
        # volcengine_coding_plan使用volcengine前缀
        if self.model.startswith('volcengine_coding_plan/'):
            return self.model.replace('volcengine_coding_plan/', 'volcengine/')
        return self.model

    def _get_litellm_params(self, messages: List[Dict], max_tokens: int = 1024) -> Dict:
        """构建litellm调用参数"""
        # 火山引擎需要设置OPENAI_API_KEY环境变量
        if self.model.startswith('volcengine/') and self.api_key:
            os.environ['OPENAI_API_KEY'] = self.api_key

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
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048
        )
        response = await acompletion(**params)

        content = response.choices[0].message.content
        try:
            json_start = content.find('[')
            json_end = content.rfind(']') + 1
            if json_start >= 0 and json_end > json_start:
                return json.loads(content[json_start:json_end])
            return []
        except json.JSONDecodeError:
            return []

    async def generate_agent_response(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]],
        contract_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        context_parts = []

        # 处理文件上下文
        if contract_context:
            if "filename" in contract_context:
                # 这是文件上下文
                original_name = contract_context.get("original_filename", contract_context["filename"])
                context_parts.append(f"用户最近上传的文件: {original_name}")
                context_parts.append(f"文件包含 {contract_context['paragraphs_count']} 个段落和 {contract_context['tables_count']} 个表格")

                # 如果有多个文件，告诉LLM
                if contract_context.get("total_files", 1) > 1:
                    context_parts.append(f"注意：此会话中总共上传了 {contract_context['total_files']} 个文件")

                context_parts.append(f"最新文件内容预览:\n{contract_context['content_preview']}")
            else:
                # 这是合同上下文
                context_parts.append(f"当前合同: {contract_context.get('name', '未命名')}")
                context_parts.append(f"合同状态: {contract_context.get('status', 'draft')}")

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
            messages.append({"role": msg["role"], "content": msg["content"]})

        if context_parts:
            user_content = f"上下文信息：\n{'\n'.join(context_parts)}\n\n用户消息：{user_message}"
        else:
            user_content = user_message

        messages.append({"role": "user", "content": user_content})

        params = self._get_litellm_params(
            messages=messages,
            max_tokens=1024
        )
        response = await acompletion(**params)

        content = response.choices[0].message.content

        # 提取token使用统计
        token_usage = {}
        if hasattr(response, 'usage'):
            token_usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }

        try:
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                result = json.loads(content[json_start:json_end])
                result["token_usage"] = token_usage

                # 确保message字段不为空
                if not result.get("message") or not result["message"].strip():
                    result["message"] = "抱歉，我暂时无法处理这个请求。请稍后重试或换一个问题。"

                return result
        except json.JSONDecodeError:
            pass

        return {
            "message": content if content and content.strip() else "抱歉，我暂时无法处理这个请求。请稍后重试。",
            "options": [],
            "token_usage": token_usage
        }

    async def review_contract(self, text_content: str) -> Dict[str, Any]:
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
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048
        )
        response = await acompletion(**params)

        content = response.choices[0].message.content
        try:
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                return json.loads(content[json_start:json_end])
        except json.JSONDecodeError:
            pass

        return {"summary": "无法解析审查结果", "issues": []}

    async def generate_react_response(
        self,
        system_prompt: str,
        conversation: List[Dict],
        tools: List[Dict]
    ) -> Dict[str, Any]:
        """生成 ReAct 响应（原生 function calling）"""
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(conversation)

        params = self._get_litellm_params(
            messages=messages,
            max_tokens=1024
        )

        # 添加工具定义（tools 已经是 OpenAI 格式）
        params["tools"] = tools
        params["tool_choice"] = "auto"

        response = await acompletion(**params)
        message = response.choices[0].message

        # 返回 content + tool_calls 结构
        tool_calls = []
        if hasattr(message, 'tool_calls') and message.tool_calls:
            for tc in message.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": json.loads(tc.function.arguments or "{}")
                })

        return {
            "content": message.content or "",
            "tool_calls": tool_calls
        }
