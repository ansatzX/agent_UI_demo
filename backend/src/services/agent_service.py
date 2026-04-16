from sqlmodel import Session, select
from typing import List, Dict, Any, Optional
from ..models.contract import Contract
from ..models.message import Message
from ..schemas.chat import Option
from .llm_service import LLMService
from .contract_service import ContractService
from .template_service import TemplateService
from .session_service import SessionService
from .react_agent import ReActAgent, AgentResult
from .tool_registry import ToolRegistry
import time


class AgentService:
    def __init__(
        self,
        session: Session,
        llm_service: LLMService,
        contract_service: ContractService,
        template_service: TemplateService,
        tool_registry: ToolRegistry = None,
        mcp_client = None,
        doc_generator = None
    ):
        self.session = session
        self.llm_service = llm_service
        self.contract_service = contract_service
        self.template_service = template_service
        self.session_service = SessionService()
        self.tools = tool_registry
        self.mcp_client = mcp_client
        self.doc_generator = doc_generator

        # 初始化 ReAct Agent
        if tool_registry:
            self.react_agent = ReActAgent(llm_service, tool_registry)
        else:
            self.react_agent = None

    async def handle_message(
        self,
        user_message: str,
        session_id: Optional[str] = None,
        option_id: Optional[str] = None,
        uploaded_file: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        # 获取或创建会话
        session_id = self.session_service.get_or_create_session(session_id)

        # 保存用户消息到JSONL，包含文件信息
        self.session_service.add_message(
            session_id,
            "user",
            user_message,
            uploaded_file=uploaded_file
        )

        # 记录开始时间
        start_time = time.time()

        # 构建上下文：前端传了文件就用前端的，否则从 session 恢复最近上传文件
        context = {}
        if uploaded_file:
            context["uploaded_file"] = uploaded_file
        else:
            session_file = self.session_service.get_session_file(session_id)
            if session_file:
                context["uploaded_file"] = {
                    "filename": session_file.get("filename"),
                    "original_filename": session_file.get("original_filename"),
                    "content": session_file.get("content")
                }

        # 使用 ReAct Agent 处理消息
        if self.react_agent:
            # 读取历史消息（排除刚添加的当前用户消息）供 Agent 有上下文
            all_messages = self.session_service.get_messages(session_id)
            history = [
                {"role": m["role"], "content": m["content"]}
                for m in all_messages[:-1]
                if m.get("role") in ("user", "assistant") and m.get("content")
            ]

            result = await self.react_agent.run(user_message, context, history=history)

            response_time = time.time() - start_time

            # 保存 Agent 响应
            options_dict = result.options if result.options else []
            self.session_service.add_message(
                session_id,
                "assistant",
                result.message,
                options_dict,
                tool_results=result.tool_results
            )

            return {
                "message": result.message,
                "options": result.options,
                "session_id": session_id,
                "response_time": response_time,
                "tool_results": result.tool_results
            }
        else:
            # 回退到旧的逻辑
            if option_id:
                response = await self._handle_option(option_id, None, None)
            else:
                # 从JSONL获取对话历史
                messages = self.session_service.get_messages(session_id)
                conversation_history = [
                    {"role": m["role"], "content": m["content"]}
                    for m in messages[:-1]  # 排除刚添加的用户消息
                ]

                # 获取会话关联的所有文件
                session_files = self.session_service.get_session_files(session_id)
                file_context = None
                if session_files:
                    # 只取最新的文件作为上下文（避免token过多）
                    latest_file = session_files[-1]
                    if latest_file and latest_file.get("content"):
                        file_content = latest_file["content"]
                        full_text = file_content.get("full_text", "")
                        file_context = {
                            "filename": latest_file["filename"],
                            "original_filename": latest_file.get("original_filename"),
                            # 根据文件大小动态调整预览长度
                            "content_preview": full_text[:300] if len(full_text) > 300 else full_text,
                            "paragraphs_count": len(file_content.get("paragraphs", [])),
                            "tables_count": len(file_content.get("tables", [])),
                            "total_files": len(session_files)  # 告诉LLM有多少个文件
                        }

                # 调用LLM生成响应
                response = await self.llm_service.generate_agent_response(
                    user_message=user_message,
                    conversation_history=conversation_history,
                    contract_context=file_context
                )

            # 计算响应时间
            response_time = time.time() - start_time

            ai_message = response.get("message", "")
            options = response.get("options", [])
            token_usage = response.get("token_usage", {})

            # 保存AI消息到JSONL
            options_dict = [opt.model_dump() if hasattr(opt, 'model_dump') else opt for opt in options]
            self.session_service.add_message(session_id, "assistant", ai_message, options_dict)

            return {
                "message": ai_message,
                "options": options,
                "session_id": session_id,
                "token_usage": token_usage,
                "response_time": response_time
            }

    async def handle_form_submission(
        self,
        form_id: str,
        values: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """处理表单提交"""
        # 检查 ReAct Agent 是否启用
        if self.react_agent is None:
            raise RuntimeError("ReAct Agent 未启用，无法处理表单提交")

        # 保存表单数据
        self.session_service.add_message(
            session_id,
            "user",
            f"提交表单数据",
            form_values=values
        )

        # 从 session 恢复最近上传文件到上下文
        context = {"form_values": values}
        session_file = self.session_service.get_session_file(session_id)
        if session_file:
            context["uploaded_file"] = {
                "filename": session_file.get("filename"),
                "original_filename": session_file.get("original_filename"),
                "content": session_file.get("content")
            }

        # 读取历史消息（排除刚添加的表单提交消息）
        all_messages = self.session_service.get_messages(session_id)
        history = [
            {"role": m["role"], "content": m["content"]}
            for m in all_messages[:-1]
            if m.get("role") in ("user", "assistant") and m.get("content")
        ]

        # 继续 Agent 循环
        result = await self.react_agent.run(
            f"用户已提交表单数据",
            context,
            history=history
        )

        # 保存响应
        self.session_service.add_message(
            session_id, "assistant", result.message, result.options, tool_results=result.tool_results
        )

        return {
            "message": result.message,
            "options": result.options,
            "session_id": session_id,
            "tool_results": result.tool_results
        }

    async def _handle_option(
        self,
        option_id: str,
        contract_id: Optional[int],
        contract_context: Optional[Dict]
    ) -> Dict[str, Any]:
        option_actions = {
            "upload_template": self._option_upload_template,
            "select_template": self._option_select_template,
            "create_contract": self._option_create_contract,
            "fill_contract": self._option_fill_contract,
            "review_contract": self._option_review_contract,
            "explain_process": self._option_explain_process,
        }

        handler = option_actions.get(option_id)
        if handler:
            return await handler(contract_id, contract_context)

        return {
            "message": "好的，让我们继续。请问您需要什么帮助？",
            "options": await self._get_default_options(contract_id)
        }

    async def _option_upload_template(self, contract_id, context):
        templates = self.template_service.list_templates()
        options = []

        for t in templates:
            options.append(Option(
                id=f"use_template_{t.id}",
                label=f"使用: {t.name}",
                description=f"使用{t.type}模板创建合同",
                action="select_template"
            ))

        options.append(Option(
            id="upload_new",
            label="上传新模板",
            description="上传您的自定义Word模板",
            action="upload_template"
        ))

        return {
            "message": "您可以上传自己的Word模板，或者选择已有的模板。",
            "options": options
        }

    async def _option_select_template(self, contract_id, context):
        templates = self.template_service.list_templates()

        if not templates:
            return {
                "message": "还没有可用的模板，请先上传一个。",
                "options": [
                    Option(id="upload_template", label="上传模板", description="上传Word合同模板", action="upload_template")
                ]
            }

        options = []
        for t in templates:
            options.append(Option(
                id=f"create_contract_{t.id}",
                label=t.name,
                description=f"基于此模板创建合同",
                action="create_contract"
            ))

        return {
            "message": "请选择要使用的模板：",
            "options": options
        }

    async def _option_create_contract(self, contract_id, context):
        if contract_id:
            return await self._option_fill_contract(contract_id, context)

        return {
            "message": "好的，请先上传或选择一个模板，然后我们就可以开始创建合同了。",
            "options": await self._get_default_options(None)
        }

    async def _option_fill_contract(self, contract_id, context):
        if not contract_id:
            return {
                "message": "请先创建一个合同。",
                "options": await self._get_default_options(None)
            }

        return {
            "message": "好的，让我们来填写合同。您可以在右侧面板中看到需要填写的字段。",
            "options": [
                Option(id="review_contract", label="审查合同", description="检查合同风险", action="review_contract"),
                Option(id="save_draft", label="保存草稿", description="保存当前进度", action="save_draft"),
            ]
        }

    async def _option_review_contract(self, contract_id, context):
        return {
            "message": "我来帮您审查一下合同，看看有没有需要注意的风险点。",
            "options": await self._get_default_options(contract_id)
        }

    async def _option_explain_process(self, contract_id, context):
        return {
            "message": """合同审批流程通常包括以下步骤：

1️⃣ **合同起草** - 填写合同信息
2️⃣ **部门初审** - 部门负责人审核
3️⃣ **法务审查** - 法务部合规检查
4️⃣ **领导审批** - 分管领导签字
5️⃣ **合同签署** - 双方盖章签署

您现在在哪个阶段呢？""",
            "options": await self._get_default_options(contract_id)
        }

    async def _get_default_options(self, contract_id: Optional[int]) -> List[Option]:
        options = []

        if contract_id:
            options.extend([
                Option(id="fill_contract", label="填写合同", description="继续填写合同内容", action="fill_contract"),
                Option(id="review_contract", label="审查合同", description="检查合同风险", action="review_contract"),
            ])
        else:
            options.extend([
                Option(id="upload_template", label="上传模板", description="上传Word合同模板", action="upload_template"),
                Option(id="select_template", label="选择模板", description="从已有模板中选择", action="select_template"),
            ])

        options.append(
            Option(id="explain_process", label="了解流程", description="查看合同审批流程", action="explain_process")
        )

        return options

    def _get_contract_context(self, contract_id: Optional[int]) -> Optional[Dict[str, Any]]:
        """获取合同上下文信息"""
        if not contract_id:
            return None

        contract = self.session.get(Contract, contract_id)
        if not contract:
            return None

        return {
            "name": contract.name,
            "status": contract.status,
            "template_id": contract.template_id
        }

    def _get_conversation_history(self, contract_id: Optional[int]) -> List[Dict[str, str]]:
        if not contract_id:
            return []

        messages = self.session.exec(
            select(Message)
            .where(Message.contract_id == contract_id)
            .order_by(Message.timestamp)
        ).all()

        return [{"role": m.role, "content": m.content} for m in messages]

    def _save_message(
        self,
        contract_id: Optional[int],
        role: str,
        content: str,
        options: List = None
    ) -> Message:
        msg = Message(
            contract_id=contract_id,
            role=role,
            content=content
        )
        if options:
            # 把Option对象转成dict
            options_dict = []
            for opt in options:
                if hasattr(opt, 'model_dump'):
                    options_dict.append(opt.model_dump())
                elif isinstance(opt, dict):
                    options_dict.append(opt)
                else:
                    options_dict.append({
                        'id': getattr(opt, 'id', ''),
                        'label': getattr(opt, 'label', ''),
                        'description': getattr(opt, 'description', ''),
                        'action': getattr(opt, 'action', '')
                    })
            msg.options = options_dict

        self.session.add(msg)
        self.session.commit()
        self.session.refresh(msg)
        return msg
