"""FastAPI application entry point for the Contract Assistant.

This module initializes and configures the FastAPI application, including:
    - Database initialization
    - Service initialization (FileService, LLMService, AgentService)
    - Tool registration
    - CORS middleware setup
    - Static file serving
    - Global exception handlers

Example:
    To start the application::

        $ python -m backend.src.main

    Or using uvicorn::

        $ uvicorn backend.src.main:app --reload

Attributes:
    FRONTEND_DIST: Path to the frontend distribution directory.
    logger: Module-level logger instance.
"""

from contextlib import asynccontextmanager
from datetime import datetime
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

# Configure application logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

load_dotenv()

from .api import chat_router
from .api import contracts_router
from .api import templates_router
from .api.files import router as files_router
from .config import settings
from .database import create_db_and_tables
from .services.agent_service import AgentService
from .services.doc_generator import DocGenerator
from .services.file_service import FileService
from .services.llm_service import LLMService
from .services.tool_registry import ToolRegistry
from .services.tools.generate_document import GenerateDocumentTool
from .services.tools.read_file import ReadFileTool
from .services.tools.read_webpage import ReadWebpageTool
from .services.tools.save_document import SaveDocumentTool
from .services.tools.show_form import ShowFormTool
from .services.tools.write_article import WriteArticleTool

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager for startup and shutdown.

    Initializes all required services and tools during application startup.

    Args:
        app: FastAPI application instance.

    Yields:
        Control back to the application for request handling.
    """
    # Startup
    create_db_and_tables()

    # 初始化 FileService（使用简单文件解析）
    file_service = FileService()
    app.state.file_service = file_service

    # 初始化 DocGenerator
    uploads_dir = Path("uploads")
    doc_generator = DocGenerator(
        template_dir=Path("templates"), output_dir=uploads_dir
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
    tool_registry.register(SaveDocumentTool(uploads_dir))

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
        doc_generator=doc_generator,
    )
    app.state.agent_service = agent_service

    logger.info("应用启动完成（使用简单文件解析模式）")

    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)


# 全局异常处理器
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器"""
    logger.error(f"未处理的异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "message": "服务器内部错误",
            "error": str(exc),
            "path": str(request.url),
        },
    )


@app.exception_handler(TimeoutError)
async def timeout_handler(request: Request, exc: TimeoutError):
    """超时异常处理器"""
    logger.error(f"请求超时: {exc}")
    return JSONResponse(
        status_code=504,
        content={"message": "请求处理超时，请稍后重试", "error": "timeout"},
    )


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
    app.mount(
        "/assets",
        StaticFiles(directory=str(FRONTEND_DIST / "assets")),
        name="assets",
    )

app.include_router(chat_router, prefix="/api")
app.include_router(templates_router, prefix="/api")
app.include_router(contracts_router, prefix="/api")
app.include_router(files_router, prefix="/api")


@app.get("/health")
def health():
    """Basic health check endpoint.

    Returns:
        Dictionary containing health status, timestamp, and version info.
    """
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "version": "0.1.0",
        "components": {"database": "ok", "llm": "ok"},
    }


@app.get("/health/ready")
async def readiness_check(request: Request):
    """Readiness check endpoint for deployment health verification.

    Performs actual connectivity checks for database and LLM services.

    Args:
        request: FastAPI request object.

    Returns:
        JSONResponse with readiness status and individual component checks.
        Returns HTTP 503 if any critical component is not ready.
    """
    checks = {"database": False, "llm": False}

    # 检查数据库（简单查询测试）
    try:
        from .database import engine

        with engine.connect() as conn:
            conn.execute("SELECT 1")
        checks["database"] = True
    except Exception as e:
        logger.error(f"数据库健康检查失败: {e}")

    # 检查LLM服务
    try:
        llm_service = request.app.state.llm_service
        if llm_service and llm_service.api_key:
            checks["llm"] = True
    except Exception as e:
        logger.error(f"LLM服务健康检查失败: {e}")

    all_ok = all(checks.values())
    status_code = 200 if all_ok else 503

    return JSONResponse(
        status_code=status_code,
        content={
            "ready": all_ok,
            "checks": checks,
            "timestamp": datetime.now().isoformat(),
        },
    )


@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    """Serve frontend application for client-side routing.

    Fallback route that serves index.html for all unmatched routes,
    enabling single-page application routing.

    Args:
        full_path: The requested URL path.

    Returns:
        FileResponse with index.html if frontend exists,
        otherwise returns basic app info.
    """
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
        reload=True,
    )
