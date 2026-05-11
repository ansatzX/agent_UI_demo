"""单一入口 — FastAPI + Gradio 合并运行时"""

from contextlib import asynccontextmanager
from datetime import datetime
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
load_dotenv()

from .api import chat_router, contracts_router, templates_router
from .api.files import router as files_router
from .config import settings
from .database import create_db_and_tables
from .services.agent_service import AgentService
from .services.doc_generator import DocGenerator
from .services.file_service import FileService
from .services.llm_service import LLMService
from .agent_framework.tool_registry import ToolRegistry
from .services.tools.generate_document import GenerateDocumentTool
from .services.tools.read_file import ReadFileTool
from .services.tools.read_webpage import ReadWebpageTool
from .services.tools.save_document import SaveDocumentTool
from .services.tools.show_form import ShowFormTool
from .services.tools.write_article import WriteArticleTool
from .services.tools.deep_research import DeepResearchTool
from .services.tools.web_search import WebSearchTool
from .services.tools.check_state import CheckStateTool

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Database ──────────────────────────────────────────────────────
    create_db_and_tables()

    # ── Core services ─────────────────────────────────────────────────
    file_service = FileService()
    app.state.file_service = file_service

    uploads_dir = Path("uploads")
    doc_generator = DocGenerator(
        template_dir=Path("templates"), output_dir=uploads_dir
    )
    app.state.doc_generator = doc_generator

    llm_service = LLMService()
    app.state.llm_service = llm_service

    # ── Tool registry (unified — all tools in one place) ──────────────
    tool_registry = ToolRegistry()
    tool_registry.register(ReadFileTool())
    tool_registry.register(ReadWebpageTool())
    tool_registry.register(WriteArticleTool())
    tool_registry.register(GenerateDocumentTool(doc_generator, uploads_dir))
    tool_registry.register(ShowFormTool())
    tool_registry.register(SaveDocumentTool(uploads_dir))
    tool_registry.register(WebSearchTool(llm_service=llm_service))
    # Shared research state holder accessible by both API and Gradio
    class _ResearchHolder:
        _active_research = None
    research_holder = _ResearchHolder()
    app.state.research_holder = research_holder

    tool_registry.register(DeepResearchTool(llm_service=llm_service, state_holder=research_holder))
    tool_registry.register(CheckStateTool(state_holder=research_holder))
    app.state.tool_registry = tool_registry

    # ── Agent service (FastAPI routes use this) ───────────────────────
    agent_service = AgentService(
        session=None,
        llm_service=llm_service,
        contract_service=None,
        template_service=None,
        tool_registry=tool_registry,
        mcp_client=None,
        doc_generator=doc_generator,
    )
    app.state.agent_service = agent_service

    # ── MCP bridge (shared) ───────────────────────────────────────────
    from .agent_framework.mcp_bridge import MCPBridge
    mcp_bridge = MCPBridge()
    app.state.mcp_bridge = mcp_bridge

    # ── Hotspot runtime ───────────────────────────────────────────────
    from .hotspots.analyzer import LLMTopicAnalyzer
    from .hotspots.collectors.jina_deepsearch import JinaDeepSearchCollector
    from .hotspots.collectors.zhihu_mcp import ZhihuMCPCollector
    from .hotspots.profile import load_creator_profile
    from .hotspots.workflow import HotspotWorkflow, render_topic_cards_markdown
    from .hotspots.history import HotspotHistoryStore
    from .agent_framework.mcp_config import load_mcp_server_configs

    profile_path = settings.project_root / "backend" / "config" / "hotspot_profile.toml"
    profile = load_creator_profile(profile_path)

    zhihu = ZhihuMCPCollector(mcp_bridge, server_name="zhihu")
    jina_api_key = os.getenv("AIHUBMIX_API_KEY")
    jina_base = os.getenv("AIHUBMIX_BASE_URL", "https://aihubmix.com/v1")
    jina = JinaDeepSearchCollector(api_key=jina_api_key, base_url=jina_base)
    analyzer = LLMTopicAnalyzer(llm_service)

    hotspot_workflow = HotspotWorkflow(
        profile=profile,
        collectors=[zhihu, jina],
        analyzer=analyzer,
        llm_service=llm_service,
        web_search=WebSearchTool(llm_service=llm_service),
    )

    history_store = HotspotHistoryStore(
        settings.project_root / "sessions" / "hotspot_runs.jsonl"
    )

    app.state.hotspot_runtime = {
        "profile": profile,
        "zhihu_collector": zhihu,
        "jina_collector": jina,
        "analyzer": analyzer,
        "workflow": hotspot_workflow,
        "render": render_topic_cards_markdown,
        "history_store": history_store,
        "mcp_config_path": settings.project_root / "backend" / "mcp_config.json",
        "load_mcp_configs": load_mcp_server_configs,
    }

    logger.info("统一运行时启动完成")
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

# ── Exception handlers ─────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"未处理异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"message": "服务器内部错误", "error": str(exc), "path": str(request.url)},
    )

@app.exception_handler(TimeoutError)
async def timeout_handler(request: Request, exc: TimeoutError):
    logger.error(f"请求超时: {exc}")
    return JSONResponse(
        status_code=504,
        content={"message": "请求处理超时", "error": "timeout"},
    )

# ── Middleware ─────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API routes ─────────────────────────────────────────────────────────────

app.include_router(chat_router, prefix="/api")
app.include_router(templates_router, prefix="/api")
app.include_router(contracts_router, prefix="/api")
app.include_router(files_router, prefix="/api")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "version": "0.1.0",
        "components": {"database": "ok", "llm": "ok"},
    }

@app.get("/health/ready")
async def readiness_check(request: Request):
    checks = {"database": False, "llm": False}
    try:
        from .database import engine
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        checks["database"] = True
    except Exception as e:
        logger.error(f"数据库健康检查失败: {e}")
    try:
        llm_service = request.app.state.llm_service
        if llm_service and getattr(llm_service, 'api_key', None):
            checks["llm"] = True
    except Exception as e:
        logger.error(f"LLM服务健康检查失败: {e}")
    all_ok = all(checks.values())
    return JSONResponse(
        status_code=200 if all_ok else 503,
        content={"ready": all_ok, "checks": checks, "timestamp": datetime.now().isoformat()},
    )


# ── Mount Gradio ───────────────────────────────────────────────────────────

class _LazyState:
    """Proxy that resolves app.state attributes at access time."""
    def __init__(self, get_state):
        self._get_state = get_state
    def __getattr__(self, name):
        return getattr(self._get_state(), name)

try:
    import gradio as gr
    from .gradio_app.app import create_gradio_blocks

    # Build Gradio with lazy state — resolves when handler actually calls
    _state = _LazyState(lambda: app.state)
    demo = create_gradio_blocks(_state)
    gr.mount_gradio_app(app, demo, path="/")
    logger.info("Gradio 已挂载到 /")
except Exception as exc:
    logger.warning("Gradio 挂载失败: %s", exc)

