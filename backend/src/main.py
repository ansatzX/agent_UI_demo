from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from contextlib import asynccontextmanager
import os
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

load_dotenv()

from .config import settings
from .database import create_db_and_tables
from .api import chat_router, templates_router, contracts_router
from .api.files import router as files_router
from .services.file_service import FileService
from .services.tool_registry import ToolRegistry
from .services.tools.read_file import ReadFileTool
from .services.tools.generate_document import GenerateDocumentTool
from .services.tools.show_form import ShowFormTool
from .services.tools.read_webpage import ReadWebpageTool
from .services.tools.write_article import WriteArticleTool
from .services.doc_generator import DocGenerator
from .services.llm_service import LLMService
from .services.agent_service import AgentService

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    create_db_and_tables()

    # 初始化 FileService（使用简单文件解析）
    file_service = FileService()
    app.state.file_service = file_service

    # 初始化 DocGenerator
    uploads_dir = Path("uploads")
    doc_generator = DocGenerator(
        template_dir=Path("templates"),
        output_dir=uploads_dir
    )
    app.state.doc_generator = doc_generator

    # 初始化 Tool Registry
    tool_registry = ToolRegistry()

    # 注册工具
    tool_registry.register(ReadFileTool())
    tool_registry.register(GenerateDocumentTool(doc_generator, uploads_dir))
    tool_registry.register(ShowFormTool())
    tool_registry.register(ReadWebpageTool())
    tool_registry.register(WriteArticleTool())

    app.state.tool_registry = tool_registry

    # 初始化 LLM Service
    llm_service = LLMService()
    app.state.llm_service = llm_service

    # 初始化 Agent Service
    agent_service = AgentService(
        session=None,
        llm_service=llm_service,
        contract_service=None,
        template_service=None,
        tool_registry=tool_registry,
        mcp_client=None,
        doc_generator=doc_generator
    )
    app.state.agent_service = agent_service

    logger.info("应用启动完成（使用简单文件解析模式）")

    yield

app = FastAPI(title=settings.app_name, lifespan=lifespan)

# 前端静态文件路径
FRONTEND_DIST = Path(__file__).parent.parent.parent / "frontend" / "dist"

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 先挂载静态文件
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")

app.include_router(chat_router, prefix="/api")
app.include_router(templates_router, prefix="/api")
app.include_router(contracts_router, prefix="/api")
app.include_router(files_router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}


# 前端路由回退
@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    if FRONTEND_DIST.exists():
        index_path = FRONTEND_DIST / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
    return {"message": settings.app_name, "version": "0.1.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.src.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=True
    )
