from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv
import os
from pathlib import Path

load_dotenv()

from .config import settings
from .database import create_db_and_tables
from .api import chat_router, templates_router, contracts_router
from .api.files import router as files_router

app = FastAPI(title=settings.app_name)

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


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


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
